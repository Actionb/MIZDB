from collections import OrderedDict
from itertools import chain

from django import views
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.utils import IntegrityError
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.translation import gettext

from DBentry import models as _models
from DBentry import utils
from DBentry.base.views import MIZAdminMixin
from DBentry.bulk.forms import BulkFormAusgabe
from DBentry.logging import LoggingMixin
from DBentry.m2m import m2m_audio_ausgabe
from DBentry.sites import register_tool


@register_tool(url_name='bulk_ausgabe', index_label='Ausgaben Erstellung')
class BulkAusgabe(MIZAdminMixin, PermissionRequiredMixin, views.generic.FormView, LoggingMixin):
    """A FormView that creates multiple ausgabe instances from a single form."""

    template_name = 'admin/bulk.html'
    form_class = BulkFormAusgabe
    permission_required = ['DBentry.add_ausgabe']
    # 'preview_fields' determines what formfields may show up in the preview as
    # columns and sets their order.
    preview_fields = [
        'magazin', 'jahrgang', 'jahr', 'num', 'monat', 'lnum', 'audio',
        'audio_lagerort', 'ausgabe_lagerort', 'provenienz'
    ]

    def get_initial(self):
        """
        Use data of the previously submitted form stored in the current session
        as this form's initial data.
        """
        return self.request.session.get('old_form_data', {})

    def post(self, request, *args, **kwargs):
        """
        Either:
            - show the preview for *this* form
            - save the data from this form and continue to the next form
            - save the data and return to the changelist
        """
        context = self.get_context_data(**kwargs)
        form = self.get_form()
        if not form.is_valid():
            return self.render_to_response(context)

        if form.has_changed() and '_preview' not in request.POST:
            # The form has changed and the user did not request a preview:
            # complain about it.
            messages.warning(
                request, 'Angaben haben sich geändert. '
                'Bitte kontrolliere diese in der Vorschau.'
            )
        elif '_addanother' in request.POST:
            # Save the data, notify the user about changes and prepare the
            # next view.
            ids, created, updated = self.save_data(form)
            if created:
                # Message about created instances.
                obj_list = utils.link_list(request, created)
                messages.success(
                    request,
                    format_html('Ausgaben erstellt: {}', obj_list)
                )
            if updated:
                # Message about updated instances.
                obj_list = utils.link_list(request, updated)
                messages.success(
                    request,
                    format_html('Dubletten hinzugefügt: {}', obj_list)
                )
            if created or updated:
                changelist_link = utils.get_changelist_link(
                    _models.ausgabe,
                    request.user,
                    obj_list=[*created, *updated]
                )
                messages.success(
                    request,
                    format_html('Zur Ausgabenübersicht: {}', changelist_link)
                )
            # Prepare the form for the next view.
            form = self.form_class(data=self.next_initial_data(form))
        elif '_continue' in request.POST:
            # Save the data and redirect back to the changelist.
            ids, instances, updated = self.save_data(form)
            return redirect(
                utils.get_changelist_url(
                    model=_models.ausgabe,
                    user=request.user,
                    obj_list=[*instances, *updated]
                )
            )

        # Add the preview.
        headers, data = self.build_preview(request, form)
        context['preview_headers'] = headers
        context['preview'] = data
        # Update the 'form' context, in case the variable was replaced
        # with the 'next' form (see '_addanother').
        context['form'] = form
        # Provide the next form with initial so we can track data changes
        # within the form.
        request.session['old_form_data'] = form.data
        return self.render_to_response(context)

    @transaction.atomic()
    def save_data(self, form):
        """
        Create or update model instances from the form's 'row_data'.

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

        # Split row_data into rows of duplicates and originals, so we save the
        # originals before any duplicates This assumes row_data does not contain
        # any nested duplicates. Also filter out rows that resulted in multiple
        # matching existing instances.
        for row in form.row_data:
            if 'multiples' in row:
                continue
            if 'dupe_of' in row:
                dupes.append(row)
            else:
                original.append(row)

        for row in chain(original, dupes):
            if 'dupe_of' in row:
                instance = row['dupe_of']['instance']
                # Since this is a duplicate of another row,
                # form.row_data has set lagerort to dublette.
                bestand_data = dict(lagerort=row.get('ausgabe_lagerort'))
                if 'provenienz' in row['dupe_of']:
                    # Also add the provenienz of the original to this object's
                    # bestand.
                    bestand_data['provenienz'] = row.get('provenienz')
                bestand = instance.bestand_set.create(**bestand_data)
                self.log_addition(instance, bestand)
                continue

            if row.get('instance'):
                instance = row['instance']
            else:
                instance = _models.ausgabe(**self.instance_data(row))
            if not instance.pk:
                # This is a new instance, mark it as such.
                instance.save()
                self.log_addition(instance)
                created.append(instance)
            else:
                # This instance already existed, update it and mark it as such.
                updates = {}
                for k, v in self.instance_data(row).items():
                    if k == 'magazin':
                        # Should and must not update the 'magazin' field.
                        continue
                    if v and getattr(instance, k) != v:
                        # The instance's value for this field differs from
                        # the new data; include it in the update.
                        updates[k] = v

                instance.qs().update(**updates)
                self.log_update(instance.qs(), updates)
                updated.append(instance)

            # Create and/or update related sets.
            for field_name in ['jahr', 'num', 'monat', 'lnum']:
                if not row.get(field_name):
                    continue
                data = row[field_name]
                if not isinstance(data, (list, tuple)):
                    data = [data]
                accessor_name = "ausgabe_{}_set".format(field_name)
                related_manager = getattr(instance, accessor_name)
                if field_name == 'monat':
                    # ausgabe_monat is actually a m2m intermediary table
                    # between tables 'ausgabe' and 'monat'. The form values for
                    # 'monat' refer to the ordinals of the months.
                    for i, value in enumerate(data):
                        if value:
                            data[i] = _models.monat.objects.filter(ordinal=value).first()
                for value in data:
                    if not value:
                        continue
                    try:
                        with transaction.atomic():
                            related_obj = related_manager.create(
                                **{field_name: value}
                            )
                    except IntegrityError:
                        # Ignore UNIQUE constraints violations.
                        continue
                    self.log_addition(instance, related_obj)

            # All the necessary data to construct a proper name should be
            # included now, update the name.
            instance.update_name(force_update=True)

            # Handle related audio objects.
            if 'audio' in row:
                titel = 'Musik-Beilage: {magazin!s} {suffix!s}'.format(
                    magazin=row.get('magazin'),
                    suffix=instance
                )
                audio_data = {'titel': titel}
                # Use the first matching queryset result or create a new instance.
                audio_instance = _models.audio.objects.filter(**audio_data).first()
                if audio_instance is None:
                    audio_instance = _models.audio(**audio_data)
                    audio_instance.save()
                    self.log_addition(audio_instance)
                # Check if the ausgabe instance is already related to the audio
                # instance.
                is_related = m2m_audio_ausgabe.objects.filter(
                    ausgabe=instance, audio=audio_instance
                ).exists()
                if not is_related:
                    m2m_instance = m2m_audio_ausgabe(
                        ausgabe=instance,
                        audio=audio_instance
                    )
                    m2m_instance.save()
                    self.log_addition(instance, m2m_instance)
                    self.log_addition(audio_instance, m2m_instance)
                # Add bestand for the audio instance.
                bestand_data = {
                    'lagerort': form.cleaned_data.get('audio_lagerort')
                }
                if 'provenienz' in row:
                    bestand_data['provenienz'] = row.get('provenienz')
                bestand = audio_instance.bestand_set.create(**bestand_data)
                self.log_addition(audio_instance, bestand)

            # Add bestand for the ausgabe instance.
            bestand_data = {
                'lagerort': row.get('ausgabe_lagerort')
            }
            if 'provenienz' in row:
                bestand_data['provenienz'] = row.get('provenienz')
            bestand = instance.bestand_set.create(**bestand_data)
            self.log_addition(instance, bestand)

            row['instance'] = instance
            ids.append(instance.pk)
        return ids, created, updated

    def next_initial_data(self, form):
        # Use the form's uncleaned data as basis for the next form.
        # form.cleaned_data contains model instances (from using ModelChoiceFields)
        # which are not JSON serializable and thus is insuitable for storage
        # in request.session.
        data = form.data.copy()
        # Increment jahr and jahrgang.
        if form.cleaned_data.get('jahr'):
            # Get the values to be incremented from row_data's first row
            # (all rows share the same values).
            # 2018,2019 -> 2020,2021
            jahre = form.row_data[0]['jahr']
            data['jahr'] = ",".join([
                str(int(j) + len(jahre))
                for j in jahre
            ])
        if form.cleaned_data.get('jahrgang'):
            data['jahrgang'] = form.cleaned_data['jahrgang'] + 1
        return data

    def instance_data(self, row):
        """
        Return data suitable to construct a model instance with from a given row.
        """
        return {
            'jahrgang': row.get('jahrgang', None),
            'magazin': row.get('magazin'),
            'beschreibung': row.get('beschreibung', ''),
            'bemerkungen': row.get('bemerkungen', ''),
            'status': row.get('status')
        }

    def build_preview(self, request, form):
        """Prepare context variables used in the 'preview' table."""
        # Check if any of the form's rows constitute one or more already
        # existing model instances. If so, the preview needs to include the
        # 'Bereits vorhanden' and 'Datenbank' headers that will contain those
        # instances and a warning message.
        any_row_has_instances = any(
            'instance' in row or 'multiples' in row
            for row in form.row_data
        )
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
                if field_name == 'audio':
                    # Add the image for a boolean True.
                    preview_row[field_name] = format_html(
                        '<img alt="True" src="/static/admin/img/icon-yes.svg">'
                    )
                elif field_name == 'audio_lagerort' and 'audio' not in row:
                    # No need to add anything for column 'audio_lagerort' if
                    # the user does not wish to add audio instances.
                    continue
                else:
                    values_list = row[field_name] or []
                    if isinstance(values_list, list):
                        if len(values_list) == 1:
                            preview_row[field_name] = values_list[0] or ''
                        else:
                            preview_row[field_name] = ", ".join(values_list)
                    else:
                        preview_row[field_name] = values_list or ''
                # Record the field's appearance for the headers creation.
                preview_fields_used.add(field_name)

            # Add warning messages if either:
            # - an already existing instance is going to be updated OR
            # - this row is going to be ignored as multiple existing instances
            #   were found using the row's data
            if 'instance' in row:
                instances = [row.get('instance')]
            else:
                instances = list(row.get('multiples', []))
            if not instances:
                if any_row_has_instances:
                    # This row is not problematic, but some other row(s) are;
                    # add a placeholder for columns 'Instanz' and 'Datenbank'.
                    preview_row['Instanz'] = '---'
                    preview_row['Datenbank'] = '---'
            else:
                if len(instances) == 1:
                    # Add a warning icon to warn about updating an existing
                    # instance.
                    img = '<img alt="False" src="/static/admin/img/icon-alert.svg">'
                    msg = gettext(
                        "Es wird ein Dubletten-Bestand zu dieser Ausgabe hinzugefügt."
                    )
                else:
                    # Add an error icon to warn that this row will be ignored.
                    img = '<img alt="False" src="/static/admin/img/icon-no.svg">'
                    msg = gettext(
                        "Es wurden mehrere passende Ausgaben gefunden. Es soll "
                        "immer nur eine bereits bestehende Ausgabe verändert "
                        "werden: diese Zeile wird ignoriert."
                    )
                preview_row['Instanz'] = utils.link_list(request, instances)
                preview_row['Datenbank'] = format_html(img + ' ' + msg)
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
            headers += ['Bereits vorhanden', 'Datenbank']
        return headers, preview_data

    def get_context_data(self, **kwargs):
        # Add ausgabe's meta for the template.
        return super().get_context_data(opts=_models.ausgabe._meta)


class BulkAusgabeHelp(MIZAdminMixin, views.generic.TemplateView):
    """A very basic view containing some text explaining the BulkAusgabe view."""

    template_name = 'admin/help_bulk_ausgabe.html'
