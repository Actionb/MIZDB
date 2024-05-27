from typing import Any, Dict, List, Optional, Set, Tuple, Union

from django import views
from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE
from django.contrib.admin.options import InlineModelAdmin
from django.db import transaction
from django.db.models import Count, F, Model, ProtectedError, QuerySet
from django.forms import ALL_FIELDS, BaseInlineFormSet, Form
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext
from django.views.generic import FormView

from dbentry import models as _models
from dbentry.actions.base import (
    ActionConfirmationView,
    ActionMixin,
    WizardConfirmationView,
    get_object_link,
    AdminActionMixin,
    AdminActionConfirmationView,
)
from dbentry.actions.forms import (
    BrochureActionFormOptions,
    BrochureActionFormSet,
    BulkEditJahrgangForm,
    MergeConflictsFormSet,
    MergeFormSelectPrimary,
    ReplaceForm,
    AdminMergeConflictsFormSet,
)
from dbentry.admin.views import MIZAdminMixin
from dbentry.models import Magazin
from dbentry.utils.admin import create_logentry, log_addition, log_change, log_deletion
from dbentry.utils.html import get_changelist_link, link_list, get_obj_link
from dbentry.utils.merge import merge_records
from dbentry.utils.models import get_model_from_string, get_model_relations, get_updatable_fields, is_protected
from dbentry.utils.replace import replace
from dbentry.utils.summarize import get_summaries


def check_same_magazin(view: ActionConfirmationView) -> bool:
    """
    Check that all objects in the view's queryset are related to the same
    Magazin instance.
    """
    if view.queryset.values("magazin_id").distinct().count() == 1:
        return True
    else:
        view.message_user(
            request=view.request,
            level=messages.WARNING,
            message=(
                f"Aktion abgebrochen: Die ausgewählten {view.opts.verbose_name_plural} "
                "gehören zu unterschiedlichen Magazinen."
            ),
        )
        return False


class BulkEditJahrgang(MIZAdminMixin, AdminActionConfirmationView):
    """View that bulk edits the Jahrgang of a collection of Ausgabe instances."""

    title = "Jahrgang hinzufügen"
    action_name = "bulk_jg"
    action_allowed_checks = [check_same_magazin]

    display_fields = ("jahrgang", "ausgabejahr__jahr")

    form_class = BulkEditJahrgangForm

    view_helptext = (
        "Sie können hier Jahrgänge zu den ausgewählten Ausgaben hinzufügen."
        "\nWählen Sie zunächst eine Schlüssel-Ausgabe, die den Beginn eines "
        "Jahrganges darstellt, aus und geben Sie den Jahrgang dieser Ausgabe an."
        "\nDie Jahrgangswerte der anderen Ausgaben werden danach in Abständen "
        "von einem Jahr (im Bezug zur Schlüssel-Ausgabe) hochgezählt, bzw. "
        "heruntergezählt."
        "\n\nAusgaben, die keine Jahresangaben besitzen (z.B. Sonderausgaben), "
        "werden ignoriert."
        "\nWird als Jahrgang '0' eingegeben, werden die Angaben für Jahrgänge "
        "aller ausgewählten Ausgaben gelöscht."
        "\nAlle bereits vorhandenen Angaben für Jahrgänge werden überschrieben."
    )

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["choices"] = {ALL_FIELDS: self.queryset}
        return kwargs

    def get_initial(self) -> dict:
        return {
            "jahrgang": 1,
            "start": self.queryset.values_list("pk", flat=True).first(),
        }

    def perform_action(self, form_cleaned_data: dict) -> None:
        """
        Incrementally update the jahrgang for each instance.

        If the user has chosen the integer 0 for jahrgang, delete all jahrgang
        values instead.
        """
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data["jahrgang"]
        start = self.queryset.get(pk=form_cleaned_data.get("start"))

        if jg == 0:
            # User entered 0 for jahrgang.
            # Delete jahrgang data from the selected ausgaben.
            qs.update(jahrgang=None)
        else:
            qs.increment_jahrgang(start, jg)
        for obj in self.queryset:
            log_change(user_id=self.request.user.pk, obj=obj, fields=["jahrgang"])


class MergeView(WizardConfirmationView):
    """
    A view with multiple steps that merges model instances.

    In the first step (select primary step), the user selects one instance from
    the available instances to designate it as the 'primary'. All other
    instances will be merged into that primary instance.

    Optionally, the user can choose to expand the 'primary' instance. For any
    field of the primary that does not have a value, the merge will try to add
    a value from the other instances. If there are multiple values possible for
    a given field, the user will be asked to choose a value in the second step
    (merge conflict resolution step) of the process.
    """

    template_name = "mizdb/merge_records.html"
    action_name = "merge_records"
    action_allowed_checks = ["check_at_least_two_objects", "check_same_magazin", "check_same_ausgabe"]

    SELECT_PRIMARY_STEP = "0"
    CONFLICT_RESOLUTION_STEP = "1"
    form_list = [(SELECT_PRIMARY_STEP, MergeFormSelectPrimary), (CONFLICT_RESOLUTION_STEP, MergeConflictsFormSet)]

    step1_helptext = (
        "Bei der Zusammenfügung werden alle verwandten Objekte der "
        "zuvor in der Übersicht ausgewählten Datensätze dem primären "
        "Datensatz zugeteilt."
        "\nFehlen dem primären Datensatz Grunddaten und wird unten bei der "
        "entsprechenden Option ('Primären Datensatz erweitern') der Haken "
        "gesetzt, so werden die fehlenden Daten "
        "nach Möglichkeit durch Daten aus den sekundären Datensätzen ergänzt. "
        "Bereits bestehende Grunddaten des primären Datensatzes werden NICHT "
        "überschrieben."
        "\nDanach werden die sekundären Datensätze GELÖSCHT."
    )
    step2_helptext = (
        "Für die Erweiterung der Grunddaten des primären Datensatzes stehen "
        "widersprüchliche Möglichkeiten zur Verfügung."
        "\nBitte wählen Sie jeweils eine der Möglichkeiten, die für den primären "
        "Datensatz übernommen werden sollen."
    )

    view_helptext: dict = {  # type: ignore[assignment]
        SELECT_PRIMARY_STEP: step1_helptext,
        CONFLICT_RESOLUTION_STEP: step2_helptext,
    }

    def check_at_least_two_objects(self) -> bool:
        """Check that at least two objects have been selected."""
        if self.queryset.count() > 1:
            return True
        else:
            self.message_user(
                request=self.request,
                level=messages.WARNING,
                message=(
                    "Aktion abgebrochen: Es müssen mindestens zwei Objekte aus "
                    "der Liste ausgewählt werden, um diese Aktion durchzuführen."
                ),
            )
            return False

    def check_same_magazin(self) -> bool:
        """
        If merging Ausgabe instances, check that they are from the same parent
        Magazin instance.
        """
        if self.model != _models.Ausgabe:
            return True
        if self.queryset.values_list("magazin").distinct().count() == 1:
            return True
        else:
            denied_message = (
                f"Aktion abgebrochen: Die ausgewählten {self.opts.verbose_name_plural} gehören zu "
                f"unterschiedlichen {_models.Magazin._meta.verbose_name_plural}n."
            )
            self.message_user(request=self.request, message=denied_message, level=messages.WARNING)
            return False

    def check_same_ausgabe(self) -> bool:
        """
        If merging Artikel instances, check that they are from the same parent
        Ausgabe instance.
        """
        if self.model != _models.Artikel:
            return True
        if self.queryset.values("ausgabe").distinct().count() == 1:
            return True
        else:
            denied_message = (
                f"Aktion abgebrochen: Die ausgewählten {self.opts.verbose_name_plural} gehören zu "
                f"unterschiedlichen {_models.Ausgabe._meta.verbose_name_plural}."
            )
            self.message_user(request=self.request, message=denied_message, level=messages.WARNING)
            return False

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_step"] = self.steps.current
        context["title"] = gettext("Merge objects: step {}").format(str(int(self.steps.current) + 1))
        if self.steps.current == self.SELECT_PRIMARY_STEP:
            context.update(self.get_context_for_primary_step(context))
        context["view_helptext"] = self.view_helptext[self.steps.current]
        return context

    def get_context_for_primary_step(self, context: dict) -> dict:  # pragma: no cover
        """Return additional template context for the 'select primary' step."""
        queryset = self.view.add_list_display_annotations(self.queryset)
        queryset = self.view.order_queryset(queryset)
        primary_step_context = {
            "result_headers": self.view.get_result_headers(),
            "result_rows": self.view.get_result_rows(queryset),
        }
        return primary_step_context

    @property
    def updates(self) -> dict:
        """
        Data to update the 'primary' instance with.

        Prepared by `_has_merge_conflicts` during processing the first step
        (SELECT_PRIMARY_STEP) and then added to the storage by `process_step`,
        this mapping of field_name: value contains the data to
        expand 'primary' with.
        """
        if not hasattr(self, "_updates"):
            step_data = self.storage.get_step_data(self.SELECT_PRIMARY_STEP)
            # noinspection PyAttributeOutsideInit
            self._updates = step_data.get("updates", {})
        return self._updates

    def _has_merge_conflicts(self, data: dict) -> Tuple[bool, Optional[dict]]:
        """
        Determine if there is going to be a merge conflict.

        If the 'primary' is going to be expanded with values from the other
        instances and there is more than one possible value for any field,
        we have a conflict and the user needs to choose what value to keep.

        Args:
            data (dict): the cleaned form data from step 0
                (i.e. the selection of the 'primary' instance).

        Returns:
            a 2-tuple consisting of a boolean on whether there is a conflict
                and a dict (or None if no updates) of field_name: new_value for
                all the updates planned for 'primary'
        """
        # Get the 'primary' object chosen by the user and
        # exclude it from the queryset we are working with.
        try:
            original_pk = data[self.get_form_prefix() + "-primary"]
            # noinspection PyUnresolvedReferences
            primary = self.model.objects.get(pk=original_pk)
        except (KeyError, self.model.DoesNotExist):  # noqa
            return False, None
        qs = self.queryset.exclude(pk=primary.pk)

        # get_updatable_fields() returns the fields that
        # may be updated by this merge;
        # i.e. empty fields without a (default) value.
        updatable_fields = get_updatable_fields(primary)
        if not updatable_fields:
            # No updates can be done on 'primary'.
            return False, None

        has_conflict = False
        # Keep track of fields of primary that would be updated.
        # If there is more than one possible change per field, we
        # need user input to decide what change to keep.
        # This is where then the next form MergeConflictsFormSet comes in.
        updates: Dict[str, Set] = {fld_name: set() for fld_name in updatable_fields}

        for other_record_valdict in qs.values(*updatable_fields):
            for k, v in other_record_valdict.items():
                if v or isinstance(v, bool):
                    # Make v both hashable (for the set) and
                    # serializable (for the session storage).
                    updates[k].add(str(v))
                    if len(updates[k]) > 1:
                        # Another value for this field has already been
                        # found; we have found a conflict.
                        has_conflict = True

        # Sets are not JSON serializable (required for session storage):
        # turn them into lists and remove empty ones.
        updates: Dict[str, List] = {  # type: ignore[no-redef]
            fld_name: sorted(list(value_set)) for fld_name, value_set in updates.items() if value_set
        }
        return has_conflict, updates

    def process_step(self, form: Form) -> dict:
        """Check the form data whether conflict resolution needs to occur."""
        data = super().process_step(form)  # the form.data for this step
        if self.steps.current == self.CONFLICT_RESOLUTION_STEP:
            # No special processing needed for the last step.
            return data
        if not form.cleaned_data.get("expand_primary", False):
            # There can only be conflicts if the primary is to be expanded.
            has_conflict = False
        else:
            has_conflict, updates = self._has_merge_conflicts(data)
            if updates:
                # data is an instance of QueryDict and thus immutable;
                # make it mutable by copying and then add
                # the updates to it to store them in storage.
                data = data.copy()
                data["updates"] = updates
        if not has_conflict:
            # No conflict found.
            # Remove the conflict resolution form from the form list (which
            # was turned into an OrderedDict in WizardView.get_initkwargs), and
            # skip right to the last step.
            self.form_list.pop(self.CONFLICT_RESOLUTION_STEP)  # type: ignore[arg-type]
            self.storage.current_step = self.steps.last
        return data

    def get_form_kwargs(self, step: Optional[int] = None) -> dict:
        kwargs = super().get_form_kwargs(step)
        if step is None:  # pragma: no cover
            step = self.steps.current

        # Note that WizardView.get_initkwargs turns the form_list into an
        # OrderedDict.
        form_class: Union[MergeFormSelectPrimary, MergeConflictsFormSet] = self.form_list[step]
        prefix = self.get_form_prefix(step, form_class)
        if step == self.CONFLICT_RESOLUTION_STEP:
            # There is a conflict.
            # Provide the MergeConflictsFormSet with the choices for the
            # 'posval' fields.
            choices, total_forms = {}, 0

            def add_prefix(key_name: str) -> str:
                return prefix + "-" + str(total_forms) + "-" + key_name

            for fld_name, values in sorted(self.updates.items()):
                if len(values) > 1:
                    # Multiple different values possible for this field; let
                    # the user choose one.
                    choices[add_prefix("posvals")] = [(c, v) for c, v in enumerate(values)]
                    total_forms += 1

            # In order to pass 'choices' on to the individual forms of the
            # MergeConflictsFormSet, we need to wrap it in yet another dict
            # called 'form_kwargs'.
            # forms.BaseFormSet.__init__ will then do the rest for us.
            kwargs["form_kwargs"] = {"choices": choices}
        elif step == self.SELECT_PRIMARY_STEP:
            # MergeFormSelectPrimary form: choices for the selection of the
            # primary object are the objects in the queryset
            kwargs["choices"] = {prefix + "-" + form_class.PRIMARY_FIELD_NAME: self.queryset}
        return kwargs

    def get_form_initial(self, step: str) -> Union[dict, list]:
        """Return the initial data for the form or formset of the given step."""
        if step == self.CONFLICT_RESOLUTION_STEP:
            # There is a conflict.
            # Provide initial data for the hidden fields of the conflict
            # resolution form. This initial data is also used to set a better
            # label for the 'posval' field.
            initial = []
            for fld_name, values in sorted(self.updates.items()):
                if len(values) > 1:
                    # More than one value: this is a field with conflicting values.
                    initial.append(
                        {
                            "original_fld_name": fld_name,
                            "verbose_fld_name": self.opts.get_field(fld_name).verbose_name.capitalize(),
                        }
                    )
            return initial
        else:
            return super().get_form_initial(step)

    def perform_action(self, *args: Any, **kwargs: Any) -> None:
        update_data = {}
        expand = self.get_cleaned_data_for_step("0").get("expand_primary", True)
        if expand:
            if self.get_cleaned_data_for_step("1"):
                # Conflicts were handled
                for form_data in self.get_cleaned_data_for_step("1"):
                    fld_name = form_data.get("original_fld_name")
                    value = self.updates[fld_name][int(form_data.get("posvals"))]
                    update_data[fld_name] = value
            for fld_name, value in self.updates.items():
                if fld_name not in update_data:
                    # This field was not part of conflict handling
                    if isinstance(value, (list, tuple)):
                        update_data[fld_name] = value[0]
                    else:
                        update_data[fld_name] = value  # pragma: no cover
        original_pk = self.get_cleaned_data_for_step("0").get("primary", 0)
        primary = self.opts.model.objects.get(pk=original_pk)
        merge_records(primary, self.queryset, update_data, expand, user_id=self.request.user.pk)

    def done(self, *args: Any, **kwargs: Any) -> None:
        """
        Perform the action.

        If the action fails due to a ProtectedError, send a user message.
        """
        try:
            self.perform_action()
        except ProtectedError as e:
            # The merge could not be completed as there were protected objects
            # in the queryset, all changes were rolled back.
            object_name = e.protected_objects.model._meta.verbose_name_plural or "Objekte"
            message = format_html(
                "Folgende verwandte {object_name} verhinderten die Zusammenführung: {protected}",
                object_name=object_name,
                protected=link_list(self.request, e.protected_objects, namespace="admin"),
            )
            self.message_user(request=self.request, level=messages.ERROR, message=message)
        return None


class AdminMergeView(MIZAdminMixin, AdminActionMixin, MergeView):
    """MergeView for the admin site."""

    template_name = "admin/merge_records.html"
    form_list = [
        (MergeView.SELECT_PRIMARY_STEP, MergeFormSelectPrimary),
        (MergeView.CONFLICT_RESOLUTION_STEP, AdminMergeConflictsFormSet),
    ]

    def get_context_for_primary_step(self, context: dict) -> dict:
        """Return additional template context for the 'select primary' step."""
        # The template uses the django admin tag 'result_list' so that the
        # results are displayed as on the changelist. The tag requires the
        # changelist as an argument.
        cl = self.model_admin.get_changelist_instance(self.request)
        cl.result_list = self.queryset
        cl.formset = None
        # The sorting URL refers to the changelist, so don't allow sorting.
        # Trying to sort would send the user back to the changelist.
        cl.sortable_by = []
        primary_label = context["form"]["primary"].label_tag(attrs={"style": "width: 100%;"})
        return {"cl": cl, "primary_label": primary_label}


class MoveToBrochure(MIZAdminMixin, AdminActionConfirmationView):
    """A view that moves Ausgabe instances to a BaseBrochure child model."""

    template_name = "admin/movetobrochure.html"
    action_name = "moveto_brochure"
    action_allowed_checks = [check_same_magazin, "check_protected_artikel"]

    form_class = BrochureActionFormSet

    def check_protected_artikel(self) -> bool:
        """
        Check whether any of the Ausgabe are referenced through protected
        foreign keys on Artikel objects.
        """
        ausgaben_with_artikel = (
            self.queryset.annotate(artikel_count=Count("artikel")).filter(artikel_count__gt=0).order_by("magazin")
        )
        if ausgaben_with_artikel.exists():
            message = format_html(
                "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht verschoben werden können: {} ({})",
                link_list(request=self.request, obj_list=ausgaben_with_artikel, namespace="admin"),
                get_changelist_link(
                    request=self.request,
                    model=_models.Ausgabe,
                    obj_list=ausgaben_with_artikel,
                    namespace="admin",
                    blank=True,
                ),
            )
            self.message_user(request=self.request, level=messages.WARNING, message=message)
            return False
        return True

    def get_initial(self) -> List[dict]:
        values = self.queryset.annotate(magazin_beschreibung=F("magazin__beschreibung")).values_list(
            "pk", "_name", "beschreibung", "bemerkungen", "magazin_id", "magazin__magazin_name", "magazin_beschreibung"
        )
        initial = []
        for pk, _name, beschreibung, bemerkungen, magazin_id, magazin_name, magazin_beschreibung in values:
            initial.append(
                {
                    "ausgabe_id": pk,
                    "titel": f"{magazin_name} {_name}",
                    "zusammenfassung": magazin_beschreibung,
                    "beschreibung": beschreibung,
                    "bemerkungen": bemerkungen,
                    "magazin_id": magazin_id,
                }
            )
        return initial

    @property
    def magazin_instance(self) -> Magazin:
        """Return the magazin instance common to all queryset objects."""
        # At this point the checks have run and excluded the possibility
        # that the queryset contains more than one magazin.
        if not hasattr(self, "_magazin_instance"):
            ausgabe_instance = self.queryset.select_related("magazin").first()
            # noinspection PyAttributeOutsideInit
            self._magazin_instance = ausgabe_instance.magazin
        return self._magazin_instance

    @property
    def can_delete_magazin(self) -> bool:
        """Assess if the magazin instance can be deleted following the action."""
        if not hasattr(self, "_can_delete_magazin"):
            # Compare the set of all ausgabe instances of the magazin with
            # the set of the selected ausgaben.
            # If the sets match, all ausgabe instances of magazin will be
            # moved and the magazin will be open to deletion afterward.
            # noinspection PyUnresolvedReferences
            magazin_ausgabe_set = set(self.magazin_instance.ausgabe_set.values_list("pk", flat=True))
            selected = set(self.queryset.values_list("pk", flat=True))
            # noinspection PyAttributeOutsideInit
            self._can_delete_magazin = magazin_ausgabe_set == selected
        return self._can_delete_magazin

    def form_valid(self, form: Form) -> Optional[HttpResponse]:
        options_form = self.get_options_form(data=self.request.POST)
        if not options_form.is_valid():
            context = self.get_context_data(options_form=options_form)
            return self.render_to_response(context)
        self.perform_action(form.cleaned_data, options_form.cleaned_data)
        # Return to the changelist:
        return None

    def perform_action(self, form_cleaned_data: dict, options_form_cleaned_data: dict) -> None:
        protected = []
        delete_magazin = options_form_cleaned_data.get("delete_magazin", False)
        # brochure_art is guaranteed to be a valid model name due to the
        # form validation.
        brochure_art = options_form_cleaned_data.get("brochure_art", "")
        brochure_class = get_model_from_string(brochure_art)
        # Must set self._magazin_instance before we begin deleting Ausgabe
        # instances.
        magazin_instance = self.magazin_instance

        for data in form_cleaned_data:
            if not data.get("accept", False):
                continue

            # Verify that the ausgabe exists and can be deleted
            try:
                ausgabe_instance = _models.Ausgabe.objects.get(pk=data["ausgabe_id"])
            except (_models.Ausgabe.DoesNotExist, _models.Ausgabe.MultipleObjectsReturned):  # noqa
                continue
            if is_protected([ausgabe_instance]):
                protected.append(ausgabe_instance)
                continue

            # Create the brochure object
            instance_data = {"titel": data["titel"]}
            for key in ("zusammenfassung", "beschreibung", "bemerkungen"):
                if key in data and data[key]:
                    instance_data[key] = data[key]

            try:
                with transaction.atomic():
                    # noinspection PyUnresolvedReferences
                    new_brochure = brochure_class.objects.create(**instance_data)
                    # Update the bestand and delete the ausgabe
                    ausgabe_instance.bestand_set.update(ausgabe_id=None, brochure_id=new_brochure.pk)
                    ausgabejahre = ausgabe_instance.ausgabejahr_set.values_list("jahr", flat=True)
                    for jahr in ausgabejahre:
                        _models.BrochureYear.objects.create(brochure=new_brochure, jahr=jahr)
                    log_deletion(self.request.user.pk, ausgabe_instance)
                    str_ausgabe = str(ausgabe_instance)
                    ausgabe_instance.delete()
            except ProtectedError:
                protected.append(ausgabe_instance)
            else:
                message = (
                    f"Hinweis: {brochure_class._meta.verbose_name} wurde automatisch erstellt beim Verschieben von "
                    f"Ausgabe {str_ausgabe} (Magazin: {str(magazin_instance)})."
                )
                create_logentry(user_id=self.request.user.pk, obj=new_brochure, action_flag=ADDITION, message=message)
                # Log the changes to the Bestand instances:
                qs = _models.Bestand.objects.filter(brochure_id=new_brochure.pk)
                for bestand_instance in qs:
                    log_change(user_id=self.request.user.pk, obj=bestand_instance, fields=["ausgabe_id", "brochure_id"])
        # Notify the user about Ausgabe instances that could not be deleted and
        # return to the changelist - without deleting the Magazin instance
        # (since it will also be protected).
        if protected:
            message = format_html(
                "Folgende Ausgaben konnten nicht gelöscht werden: "
                "{obj_links} ({cl_link}). Es wurden keine Broschüren für "
                "diese Ausgaben erstellt.",
                obj_links=link_list(request=self.request, obj_list=protected, namespace="admin", blank=True),
                cl_link=get_changelist_link(
                    request=self.request,
                    model=_models.Ausgabe,
                    obj_list=protected,
                    namespace="admin",
                    blank=True,
                ),
            )
            self.message_user(request=self.request, level=messages.ERROR, message=message)
            return None

        # The deletion should not interrupt/rollback the deletion of
        # the ausgabe, hence we do not include it in the ausgabe transaction.
        if delete_magazin:
            try:
                with transaction.atomic():
                    magazin_instance.delete()
            except ProtectedError:
                # Seems like the magazin was still protected after all.
                message = format_html(
                    "Magazin konnte nicht gelöscht werden: {}",
                    get_obj_link(request=self.request, obj=magazin_instance, blank=True),
                )
                self.message_user(request=self.request, level=messages.ERROR, message=message)
            else:
                log_deletion(self.request.user.pk, magazin_instance)

    def get_options_form(self, **kwargs: Any) -> Form:
        """Return the form that configures this action."""
        kwargs["can_delete_magazin"] = self.can_delete_magazin
        return BrochureActionFormOptions(**kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        formset = self.get_form()
        forms = []
        for form in formset:
            link = get_obj_link(
                request=self.request, obj=_models.Ausgabe.objects.get(pk=form["ausgabe_id"].initial), blank=True
            )
            forms.append((link, form))
        context["forms"] = forms
        context["management_form"] = formset.management_form
        context["options_form"] = self.get_options_form()
        context.update(kwargs)
        return context


class ChangeBestand(AdminActionMixin, ActionMixin, MIZAdminMixin, views.generic.TemplateView):
    """A view to edit the Bestand set of the parent model instance(s)."""

    template_name = "admin/change_bestand.html"

    action_name = "change_bestand"
    action_reversible = True

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Optional[HttpResponse]:
        if "action_confirmed" in request.POST:
            # Collect all the valid formsets:
            formsets = []
            for obj in self.queryset:
                formset, inline = self.get_bestand_formset(self.request, obj)
                if formset.is_valid():
                    formsets.append(formset)
                else:
                    # Invalid formset found, abort the save process.
                    break
            else:
                self.perform_action(formsets)
                # Return to the changelist:
                return None
        return self.get(request, *args, **kwargs)

    def perform_action(self, formsets: List[BaseInlineFormSet]) -> None:  # type: ignore[override]
        with transaction.atomic():
            for formset in formsets:
                formset.save()
                self.create_log_entries(formset)

    def create_log_entries(self, formset: BaseInlineFormSet) -> None:
        """Create LogEntry objects for the parent and its related objects."""
        # We can get the correct change message for the LogEntry objects
        # of the parent instance from the model_admin's
        # construct_change_message method, which requires a form argument.
        # Since we are never changing anything on the instance itself, a very
        # basic model form will do.
        form = self.model_admin.get_form(self.request, obj=formset.instance, fields=["id"])()
        # 'add' argument is always False as we are always working on an already
        # existing parent instance.
        change_message = self.model_admin.construct_change_message(
            request=self.request, form=form, formsets=[formset], add=False
        )
        self.model_admin.log_change(self.request, formset.instance, change_message)
        # Now create LogEntry objects for the Bestand model side:
        user_id = self.request.user.pk
        for new_obj in formset.new_objects:
            log_addition(user_id, new_obj)
        for changed_obj, changed_data in formset.changed_objects:
            log_change(user_id, changed_obj, fields=changed_data)
        for deleted_obj in formset.deleted_objects:
            log_deletion(user_id, deleted_obj)

    def get_bestand_formset(self, request: HttpRequest, obj: Model) -> Tuple[BaseInlineFormSet, InlineModelAdmin]:
        """Return the Bestand formset and model admin inline for this object."""
        formsets_with_inlines = self.model_admin.get_formsets_with_inlines(request, obj)
        for formset_class, inline in formsets_with_inlines:
            if inline.model == _models.Bestand:
                break
        else:
            raise ValueError(f"Model admin '{self.model_admin}' has no inline for model Bestand!")
        formset_params = {
            "instance": obj,
            "prefix": "%s-%s" % (formset_class.get_default_prefix(), obj.pk),
            "queryset": inline.get_queryset(request),
        }
        if "action_confirmed" in request.POST:
            formset_params["data"] = request.POST.copy()
        formset = formset_class(**formset_params)
        return formset, inline

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["object_name"] = self.opts.object_name
        context["formsets"] = []
        media_updated = False
        for obj in self.queryset:
            formset, inline = self.get_bestand_formset(self.request, obj)
            # Wrap the formset into django's InlineAdminFormSet, so that we can
            # use django's edit_inline/tabular template.
            wrapped_formset = self.model_admin.get_inline_formsets(
                request=self.request, formsets=[formset], inline_instances=[inline], obj=obj
            )[0]
            if not media_updated:
                # Add the inline formset media (such as inlines.js):
                context["media"] += wrapped_formset.media
                media_updated = True
            context["formsets"].append((get_obj_link(request=self.request, obj=obj, blank=True), wrapped_formset))
        return context


class Replace(MIZAdminMixin, AdminActionConfirmationView):
    """A view to replace an object with selected objects of the same model."""

    form_class = ReplaceForm
    title = "%(verbose_name)s ersetzen"
    action_name = "replace"
    action_allowed_checks = ["_check_one_object_only"]
    action_reversible = True
    view_helptext = (
        'Ersetze %(verbose_name)s "%(object)s" durch die unten ausgewählten '
        "%(verbose_name_plural)s. "
        'Dabei werden auch die Datensätze verändert, die mit "%(object)s" verwandt sind.'
    )

    def _check_one_object_only(self) -> bool:
        """Check that the view is called with just one object."""
        if self.queryset.count() > 1:
            self.message_user(
                request=self.request,
                message=(
                    "Aktion abgebrochen: Diese Aktion kann nur mit einzelnen Datensätzen durchgeführt werden: "
                    "bitte wählen Sie nur einen Datensatz aus."
                ),
                level=messages.WARNING,
            )
            return False
        return True

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["choices"] = {"replacements": self.model.objects.all()}
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        # 'objects_name' is used in the template to address the objects of the
        # queryset. It's usually the verbose_name of the queryset's model, but
        # since the 'replace' action creates changes on a range of different
        # models, use a more generic term.
        context["objects_name"] = "Datensätze"
        context["view_helptext"] = self.view_helptext % {
            "verbose_name": self.model._meta.verbose_name,
            "verbose_name_plural": self.model._meta.verbose_name_plural,
            "object": str(self.queryset.get()),
        }
        return context

    def perform_action(self, cleaned_data: dict) -> None:  # type: ignore[override]
        obj = self.queryset.get()
        replacements = self.model.objects.filter(pk__in=cleaned_data["replacements"])
        changes = replace(obj, replacements)

        change_message = [{"deleted": {"object": str(obj), "name": obj._meta.verbose_name}}]
        for replacement in replacements:
            change_message.append({"added": {"object": str(replacement), "name": replacement._meta.verbose_name}})
        for changed_obj in changes:
            create_logentry(self.request.user.pk, changed_obj, CHANGE, change_message)
        return None

    def get_objects_list(self) -> list:
        """
        Provide links to the change pages of the records that are related with
        the object to be replaced.
        """
        to_replace = self.queryset.get()
        objects_list = []

        for rel in get_model_relations(self.model, forward=False):
            if rel.related_model == self.model:
                related_set = getattr(to_replace, rel.remote_field.name)
            else:
                related_set = getattr(to_replace, rel.get_accessor_name())

            for obj in related_set.all():
                link = get_object_link(self.request, obj, self.model_admin.admin_site.name)
                objects_list.append((link,))
        return objects_list


def text_summary(queryset: QuerySet) -> HttpResponse:
    """
    Return a HttpResponse containing a text summary of the objects in the given
    queryset.
    """
    response = HttpResponse()
    for d in get_summaries(queryset):
        for k, v in d.items():
            response.write(f"<p>{k}: {v}</p>")
        response.write('<hr style="break-after:page;">')
    return response
