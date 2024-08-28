from collections import OrderedDict
from itertools import chain
from typing import Any, List, Tuple

from django import views
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Model
from django.db.utils import IntegrityError
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.translation import gettext

from dbentry import models as _models
from dbentry.admin.views import MIZAdminMixin
from dbentry.tools.bulk.forms import BulkFormAusgabe
from dbentry.tools.decorators import register_tool
from dbentry.utils.admin import log_addition, log_change
from dbentry.utils.html import get_changelist_link, link_list
from dbentry.utils.url import get_changelist_url


@register_tool(
    url_name="tools:bulk_ausgabe", index_label="Ausgaben Erstellung", permission_required=["dbentry.add_ausgabe"]
)
class BulkAusgabe(MIZAdminMixin, PermissionRequiredMixin, views.generic.FormView):
    """A FormView that creates multiple Ausgabe instances from a single form."""

    template_name = "admin/bulk.html"
    form_class = BulkFormAusgabe
    title = "Ausgaben Erstellung"
    permission_required = ["dbentry.add_ausgabe"]
    # 'preview_fields' determines what formfields may show up in the preview as
    # columns, and sets their order.
    preview_fields = [
        "magazin",
        "jahrgang",
        "jahr",
        "num",
        "monat",
        "lnum",
        "audio",
        "audio_lagerort",
        "ausgabe_lagerort",
        "provenienz",
    ]

    def get_initial(self) -> dict:
        """
        Use data of the previously submitted form stored in the current session
        as this form's initial data.
        """
        old_form_data = self.request.session.get("old_form_data", {})
        if old_form_data:
            # Initial values need to be of the correct type for the formfield.
            # jahrgang is an IntegerField and expects an integer initial value,
            # but the old value for that field has been turned into a string by
            # the JSONSerializer. Need to cast it back into an integer or
            # has_changed() will always return true (initial string is always
            # unequal to the integer from the form data).
            if old_form_data.get("jahrgang"):
                old_form_data["jahrgang"] = int(old_form_data["jahrgang"])
            return old_form_data
        try:
            return {
                "ausgabe_lagerort": _models.Lagerort.objects.get(ort="Zeitschriftenraum"),
                "dublette": _models.Lagerort.objects.get(ort="Dublettenlager"),
            }
        except (_models.Lagerort.DoesNotExist, _models.Lagerort.MultipleObjectsReturned):  # noqa
            return {}

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Handle a POST request.

        Either:
            - show the preview for *this* form
            - save the data from this form and continue to the next form
            - save the data and return to the changelist
        """
        context = self.get_context_data(**kwargs)
        form = self.get_form()
        if not form.is_valid():
            return self.render_to_response(context)

        if form.has_changed() and "_preview" not in request.POST:
            # The form has changed and the user did not request a preview:
            # complain about it.
            messages.warning(request, "Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.")
        elif "_addanother" in request.POST:
            # Save the data, notify the user about changes and prepare the
            # next view.
            ids, created, updated = self.save_data(form)
            if created:
                # Message about created instances.
                obj_list = link_list(request, created, blank=True)
                messages.success(request, format_html("Ausgaben erstellt: {}", obj_list))
            if updated:
                # Message about updated instances.
                obj_list = link_list(request, updated, blank=True)
                messages.success(request, format_html("Dubletten hinzugefügt: {}", obj_list))
            if created or updated:
                # noinspection PyUnresolvedReferences
                changelist_link = get_changelist_link(
                    request, _models.Ausgabe, obj_list=[*created, *updated], namespace="admin", blank=True
                )
                messages.success(request, format_html("Zur Ausgabenübersicht: {}", changelist_link))
            # Prepare the form for the next view.
            form = self.form_class(data=self.next_initial_data(form))
        elif "_continue" in request.POST:
            # Save the data and redirect back to the changelist.
            ids, instances, updated = self.save_data(form)
            # noinspection PyUnresolvedReferences
            return redirect(
                get_changelist_url(
                    request,
                    model=_models.Ausgabe,
                    obj_list=[*instances, *updated],
                    namespace="admin",
                )
            )

        # Add the preview.
        headers, data = self.build_preview(request, form)
        context["preview_headers"] = headers
        context["preview"] = data
        # Update the 'form' context, in case the variable was replaced
        # with the 'next' form (see '_addanother').
        context["form"] = form
        # Provide the next form with initial, so we can track data changes
        # within the form.
        # noinspection PyUnresolvedReferences
        request.session["old_form_data"] = form.data
        return self.render_to_response(context)

    @transaction.atomic()
    def save_data(self, form: Form) -> Tuple[List[int], List[Model], List[Model]]:
        """
        Create or update model instances from the form's ``row_data``.

        Rows that are duplicates of another row or rows that resolve
        into multiple similar existing instances will not be used to create new
        instances.

        Returns a 3-tuple:
            - the list of ids of created or updated instances
            - the list of created instances
            - the list of updated instances
        """
        # Primary keys of instances either created or updated by save_data.
        ids = []
        # Instances of objects that were newly created by save_data.
        created = []
        # Instances that were existed before save_data and were updated by it.
        updated = []
        # Any unique row or the first row in a set of equal rows will be
        # recorded in 'original'.
        original = []
        # Rows in this list are a duplicate of a row in originals.
        # No new objects will be created for duplicate rows,
        # but a 'dubletten' bestand will be added to their originals.
        dupes = []

        user_id = self.request.user.pk
        # Split row_data into rows of duplicates and originals, so we save the
        # originals before any duplicates This assumes row_data does not contain
        # any nested duplicates. Also filter out rows that resulted in multiple
        # matching existing instances.
        for row in form.row_data:
            if "multiples" in row:
                continue
            if "dupe_of" in row:
                dupes.append(row)
            else:
                original.append(row)

        for row in chain(original, dupes):
            if "dupe_of" in row:
                instance = row["dupe_of"]["instance"]
                # Since this is a duplicate of another row,
                # form.row_data has set lagerort to dublette.
                bestand_data = dict(lagerort=row.get("ausgabe_lagerort"))
                if "provenienz" in row["dupe_of"]:
                    # Also add the provenienz of the original to this object's
                    # bestand.
                    bestand_data["provenienz"] = row.get("provenienz")
                bestand = instance.bestand_set.create(**bestand_data)
                log_addition(user_id, instance, bestand)
                continue

            if row.get("instance"):
                instance = row["instance"]
            else:
                instance = _models.Ausgabe(**self.instance_data(row))
            if not instance.pk:
                # This is a new instance, mark it as such.
                instance.save()
                log_addition(user_id, instance)
                created.append(instance)
            else:
                # This instance already existed, update it and mark it as such.
                updates = {}
                for k, v in self.instance_data(row).items():
                    if k == "magazin":
                        # Should and must not update the 'magazin' field.
                        continue
                    if v and getattr(instance, k) != v:
                        # The instance's value for this field differs from
                        # the new data; include it in the update.
                        updates[k] = v

                instance.qs().update(**updates)
                instance.refresh_from_db()
                log_change(user_id, instance, list(updates.keys()))
                updated.append(instance)

            # Create and/or update related sets.
            for field_name in ["jahr", "num", "monat", "lnum"]:
                if not row.get(field_name):
                    continue
                data = row[field_name]
                if isinstance(data, tuple):
                    data = list(data)  # pragma: no cover
                if not isinstance(data, list):
                    data = [data]
                accessor_name = "ausgabe{}_set".format(field_name)
                related_manager = getattr(instance, accessor_name)
                if field_name == "monat":
                    # ausgabemonat is actually a m2m intermediary table
                    # between tables 'ausgabe' and 'monat'. The form values for
                    # 'monat' refer to the ordinals of the months.
                    for i, value in enumerate(data):
                        if value:
                            data[i] = _models.Monat.objects.filter(ordinal=value).first()
                for value in data:
                    if not value:
                        continue  # pragma: no cover
                    try:
                        with transaction.atomic():
                            related_obj = related_manager.create(**{field_name: value})
                    except IntegrityError:
                        # Ignore UNIQUE constraints violations.
                        continue
                    log_addition(user_id, instance, related_obj)

            # All the necessary data to construct a proper name should be
            # included now, update the name.
            instance.update_name(force_update=True)

            # Handle related audio objects.
            if "audio" in row:
                titel = "Musik-Beilage: {magazin!s} {suffix!s}".format(magazin=row.get("magazin"), suffix=instance)
                audio_data = {"titel": titel}
                # Use the first matching queryset result or create a new instance.
                audio_instance = _models.Audio.objects.filter(**audio_data).first()
                if audio_instance is None:
                    audio_instance = _models.Audio(**audio_data)
                    audio_instance.save()
                    log_addition(user_id, audio_instance)
                # Check if the ausgabe instance is already related to the audio
                # instance.
                is_related = _models.Ausgabe.audio.through.objects.filter(
                    ausgabe=instance, audio=audio_instance
                ).exists()
                if not is_related:
                    m2m_instance = _models.Ausgabe.audio.through(ausgabe=instance, audio=audio_instance)
                    m2m_instance.save()
                    log_addition(user_id, instance, m2m_instance)
                    log_addition(user_id, audio_instance, m2m_instance)
                # Add bestand for the audio instance.
                bestand_data = {"lagerort": form.cleaned_data.get("audio_lagerort")}
                if "provenienz" in row:
                    bestand_data["provenienz"] = row.get("provenienz")
                bestand = audio_instance.bestand_set.create(**bestand_data)
                log_addition(user_id, audio_instance, bestand)

            # Add bestand for the ausgabe instance.
            bestand_data = {"lagerort": row.get("ausgabe_lagerort")}
            if "provenienz" in row:
                bestand_data["provenienz"] = row.get("provenienz")
            bestand = instance.bestand_set.create(**bestand_data)
            log_addition(user_id, instance, bestand)

            row["instance"] = instance
            ids.append(instance.pk)
        return ids, created, updated

    # noinspection PyMethodMayBeStatic
    def next_initial_data(self, form: Form) -> dict:
        """Prepare data for the next form based on this form's data."""
        # Use the form's uncleaned data as basis for the next form.
        # form.cleaned_data contains model instances (from using ModelChoiceFields)
        # which are not JSON serializable and thus is unsuitable for storage
        # in request.session.
        data = form.data.copy()
        # Increment jahr and jahrgang.
        if form.cleaned_data.get("jahr"):
            # Get the values to be incremented from row_data's first row
            # (all rows share the same values).
            # 2018,2019 -> 2020,2021
            jahre = form.row_data[0]["jahr"]
            data["jahr"] = ",".join([str(int(j) + len(jahre)) for j in jahre])
        if form.cleaned_data.get("jahrgang"):
            data["jahrgang"] = form.cleaned_data["jahrgang"] + 1
        return data

    # noinspection PyMethodMayBeStatic
    def instance_data(self, row: dict) -> dict:
        """Return data suitable to construct a model instance with from a given row."""
        return {
            "jahrgang": row.get("jahrgang", None),
            "magazin": row.get("magazin"),
            "beschreibung": row.get("beschreibung", ""),
            "bemerkungen": row.get("bemerkungen", ""),
            "status": row.get("status"),
        }

    def build_preview(self, request: HttpRequest, form: Form) -> Tuple[List[str], List[OrderedDict]]:
        """
        Prepare context variables used in the preview table.

        Returns a 2-tuple:
            - the list of table headers for the preview table
            - the list of rows for the preview table
        """
        # Check if any of the form's rows constitute one or more already
        # existing model instances. If so, the preview needs to include the
        # 'Bereits vorhanden' and 'Datenbank' headers that will contain those
        # instances and a warning message.
        any_row_has_instances = any("instance" in row or "multiples" in row for row in form.row_data)
        # Construct the preview row for the form's rows.
        preview_data = []
        # Keep track of what fields in form.preview_fields are actually showing
        # up in the preview so that we later do not add headers for columns
        # that do not exist.
        preview_fields_used = set()
        for row in form.row_data:
            preview_row = OrderedDict()
            for field_name in self.preview_fields:
                if field_name not in row:
                    continue
                if field_name == "audio":
                    # Add the image for a boolean True.
                    preview_row[field_name] = format_html('<img alt="True" src="/static/admin/img/icon-yes.svg">')
                elif field_name == "audio_lagerort" and "audio" not in row:
                    # No need to add anything for column 'audio_lagerort' if
                    # the user does not wish to add audio instances.
                    continue  # pragma: no cover
                else:
                    values_list = row[field_name] or []
                    if isinstance(values_list, list):
                        if len(values_list) == 1:
                            preview_row[field_name] = values_list[0] or ""
                        else:
                            preview_row[field_name] = ", ".join(values_list)
                    else:
                        preview_row[field_name] = values_list or ""
                # Record the field's appearance for the header creation.
                preview_fields_used.add(field_name)

            # Add warning messages if either:
            # - an already existing instance is going to be updated OR
            # - this row is going to be ignored as multiple existing instances
            #   were found using the row's data
            if "instance" in row:
                instances = [row.get("instance")]
            else:
                instances = list(row.get("multiples", []))
            if not instances:
                if any_row_has_instances:
                    # This row is not problematic, but some other row(s) are;
                    # add a placeholder for columns 'Instanz' and 'Datenbank'.
                    preview_row["Instanz"] = "---"
                    preview_row["Datenbank"] = "---"
            else:
                if len(instances) == 1:
                    # Add a warning icon to warn about updating an existing
                    # instance.
                    img = '<img alt="False" src="/static/admin/img/icon-alert.svg">'
                    msg = gettext("Es wird ein Dubletten-Bestand zu dieser Ausgabe hinzugefügt.")
                else:
                    # Add an error icon to warn that this row will be ignored.
                    img = '<img alt="False" src="/static/admin/img/icon-no.svg">'
                    msg = gettext(
                        "Es wurden mehrere passende Ausgaben gefunden. Es soll "
                        "immer nur eine bereits bestehende Ausgabe verändert "
                        "werden: diese Zeile wird ignoriert."
                    )
                preview_row["Instanz"] = link_list(request, instances, blank=True)
                preview_row["Datenbank"] = format_html(img + " " + msg)
            preview_data.append(preview_row)
        # Build the headers for the preview table.
        headers = []
        for field_name in self.preview_fields:
            if field_name not in preview_fields_used:
                # This field does not appear at least once in preview_data;
                # do not include it in the headers.
                continue
            if form.fields[field_name].label:
                headers.append(form.fields[field_name].label)
            else:
                headers.append(field_name)
        if any_row_has_instances:
            headers += ["Bereits vorhanden", "Datenbank"]
        return headers, preview_data

    def get_context_data(self, **kwargs: Any) -> dict:
        # Add ausgabe's meta for the template.
        # noinspection PyUnresolvedReferences
        return super().get_context_data(opts=_models.Ausgabe._meta)
