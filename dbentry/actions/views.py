from typing import Any, Dict, List, Optional, Set, Tuple

from django import views
from django.contrib import messages
from django.contrib.admin.models import ADDITION
from django.contrib.admin.options import InlineModelAdmin
from django.db import transaction
from django.db.models import Count, F, Model, ProtectedError
from django.forms import ALL_FIELDS, BaseInlineFormSet, Form
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy
from django.views.generic import FormView

from dbentry import models as _models
from dbentry.actions.base import (
    ActionConfirmationView, ConfirmationViewMixin, WizardConfirmationView
)
from dbentry.actions.forms import (
    BrochureActionFormOptions, BrochureActionFormSet, BulkEditJahrgangForm, MergeConflictsFormSet,
    MergeFormSelectPrimary
)
from dbentry.models import Magazin
from dbentry.utils import (
    get_changelist_link, get_model_from_string, get_obj_link, get_updatable_fields, is_protected,
    link_list, merge_records
)
from dbentry.utils.admin import (
    create_logentry, log_addition, log_change, log_deletion
)


# noinspection PyUnresolvedReferences
def check_same_magazin(view: FormView, **_kwargs: Any) -> bool:
    """
    Check that all objects in the view's queryset are related to the same
    Magazin instance.
    """
    if view.queryset.values('magazin_id').distinct().count() != 1:
        view.model_admin.message_user(
            request=view.request, level=messages.ERROR,
            message='Aktion abgebrochen: Die ausgewählten %s gehören zu '
                    'unterschiedlichen Magazinen.' % view.opts.verbose_name_plural
        )
        return False
    return True


class BulkEditJahrgang(ActionConfirmationView):
    """
    View that bulk edits the jahrgang of a collection of Ausgabe instances.
    """

    short_description = gettext_lazy("Add issue volume")
    allowed_permissions = ['change']
    action_name = 'bulk_jg'
    action_allowed_checks = [check_same_magazin]

    affected_fields = ['jahrgang', 'ausgabejahr__jahr']

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['choices'] = {ALL_FIELDS: self.queryset}
        return kwargs

    def get_initial(self) -> dict:
        return {
            'jahrgang': 1,
            'start': self.queryset.values_list('pk', flat=True).first(),
        }

    def perform_action(self, form_cleaned_data: dict) -> None:  # type: ignore[override]
        """
        Incrementally update the jahrgang for each instance.

        If the user has chosen the integer 0 for jahrgang, delete all jahrgang
        values instead.
        """
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data['jahrgang']
        start = self.queryset.get(pk=form_cleaned_data.get('start'))

        if jg == 0:
            # User entered 0 for jahrgang.
            # Delete jahrgang data from the selected ausgaben.
            qs.update(jahrgang=None)
        else:
            qs.increment_jahrgang(start, jg)
        for obj in self.queryset:
            log_change(
                user_id=self.request.user.pk, obj=obj, fields=['jahrgang']
            )


class MergeViewWizarded(WizardConfirmationView):
    """
    View that merges model instances.

    The user selects one instance from the available instances to designate
    it as the 'primary'.
    All other instances will be merged into that one instance.
    Optionally, the user can choose to expand the 'primary' with data from the
    other instances, for any fields of 'primary' that do not have a value.
    """

    template_name = 'admin/merge_records.html'
    short_description = gettext_lazy("Merge selected %(verbose_name_plural)s")
    allowed_permissions = ['merge']
    action_name = 'merge_records'
    action_allowed_checks = [
        '_check_too_few_objects',
        '_check_different_magazines',
        '_check_different_ausgaben'
    ]
    # Admin message for some failed checks.
    denied_message = (
        "Die ausgewählten {self_plural} gehören zu unterschiedlichen {other_plural}."
    )

    SELECT_PRIMARY_STEP = '0'
    CONFLICT_RESOLUTION_STEP = '1'
    form_list = [
        (SELECT_PRIMARY_STEP, MergeFormSelectPrimary),
        (CONFLICT_RESOLUTION_STEP, MergeConflictsFormSet)
    ]

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

    view_helptext = {
        SELECT_PRIMARY_STEP: step1_helptext,
        CONFLICT_RESOLUTION_STEP: step2_helptext
    }

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        # Add the current step to the view's title.
        context['title'] = gettext(
            'Merge objects: step {}'
        ).format(str(int(self.steps.current) + 1))
        if self.steps.current == self.SELECT_PRIMARY_STEP:
            # The template uses the django admin tag 'result_list' so that the
            # results are displayed as on the changelist. The tag requires the
            # changelist as an argument.
            cl = self.model_admin.get_changelist_instance(self.request)
            cl.result_list = self.queryset
            cl.formset = None
            # The sorting URL refers to the changelist, so don't allow sorting.
            # Trying to sort would send the user back to the changelist.
            cl.sortable_by = []
            context['cl'] = cl
            context['primary_label'] = context['form']['primary'].label_tag(
                attrs={'style': 'width: 100%;'}
            )
            context['current_step'] = '0'
        return context

    # noinspection PyMethodParameters
    def _check_too_few_objects(view, **_kwargs: Any) -> bool:
        """Check whether an insufficient number of objects has been selected."""
        if view.queryset.count() == 1:
            view.model_admin.message_user(
                request=view.request,
                level=messages.WARNING,
                message=(
                    'Es müssen mindestens zwei Objekte aus der Liste '
                    'ausgewählt werden, um diese Aktion durchzuführen.'
                ),
            )
            return False
        return True

    # noinspection PyMethodParameters
    def _check_different_magazines(view, **_kwargs: Any) -> bool:
        """
        Check whether the Ausgabe instances are from different Magazin instances.
        """
        if (view.model == _models.Ausgabe
                and view.queryset.values_list('magazin').distinct().count() > 1):
            # User is trying to merge ausgaben from different magazines.
            # noinspection PyUnresolvedReferences,PyProtectedMember
            format_dict = {
                'self_plural': view.opts.verbose_name_plural,
                # Add a 'n' at the end because german grammar.
                'other_plural': _models.Magazin._meta.verbose_name_plural + 'n'
            }
            view.model_admin.message_user(
                request=view.request,
                message=view.denied_message.format(**format_dict),
                level=messages.ERROR
            )
            return False
        return True

    # noinspection PyMethodParameters
    def _check_different_ausgaben(view, **_kwargs: Any) -> bool:
        """
        Check whether the Artikel instances are from different Ausgabe instances.
        """
        if (view.model == _models.Artikel
                and view.queryset.values('ausgabe').distinct().count() > 1):
            # User is trying to merge artikel from different ausgaben.
            # noinspection PyProtectedMember,PyUnresolvedReferences
            format_dict = {
                'self_plural': view.opts.verbose_name_plural,
                'other_plural': _models.Ausgabe._meta.verbose_name_plural
            }
            view.model_admin.message_user(
                request=view.request,
                message=view.denied_message.format(**format_dict),
                level=messages.ERROR
            )
            return False
        return True

    # noinspection PyAttributeOutsideInit
    @property
    def updates(self) -> dict:
        """
        Data to update the 'primary' instance with.

        Prepared by `_has_merge_conflicts` during processing the first step
        (SELECT_PRIMARY_STEP) and then added to the storage by `process_step`,
        this mapping of field_name: value contains the data to
        expand 'primary' with.
        """
        if not hasattr(self, '_updates'):
            step_data = self.storage.get_step_data(self.SELECT_PRIMARY_STEP)
            self._updates = step_data.get('updates', {})
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
        # noinspection PyUnresolvedReferences
        try:
            original_pk = data[self.get_form_prefix() + '-primary']
            # noinspection PyUnresolvedReferences
            primary = self.model.objects.get(pk=original_pk)
        except (KeyError, self.model.DoesNotExist):
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
            fld_name: list(value_set) for fld_name, value_set in updates.items() if value_set}
        return has_conflict, updates

    def process_step(self, form: Form) -> dict:
        """Check the form data whether conflict resolution needs to occur."""
        data = super().process_step(form)  # the form.data for this step
        if self.steps.current == self.CONFLICT_RESOLUTION_STEP:
            # No special processing needed for the last step.
            return data
        if not form.cleaned_data.get('expand_primary', False):
            # There can only be conflicts if the primary is to be expanded.
            has_conflict = False
        else:
            has_conflict, updates = self._has_merge_conflicts(data)
            if updates:
                # data is an instance of QueryDict and thus immutable;
                # make it mutable by copying and then add
                # the updates to it to store them in storage.
                data = data.copy()
                data['updates'] = updates
        if not has_conflict:
            # No conflict found;
            # Set the current_step to the CONFLICT_RESOLUTION_STEP
            # so that the conflict resolution will be skipped.
            self.storage.current_step = self.CONFLICT_RESOLUTION_STEP
        return data

    def get_form_kwargs(self, step: Optional[int] = None) -> dict:
        kwargs = super().get_form_kwargs(step)
        if step is None:  # pragma: no cover
            step = self.steps.current
        # Note that WizardView.get_initkwargs turns the form_list into an
        # OrderedDict.
        # noinspection PyTypeChecker
        form_class: MergeFormSelectPrimary = self.form_list[step]  # type: ignore[assignment]
        prefix = self.get_form_prefix(step, form_class)
        if step == self.CONFLICT_RESOLUTION_STEP:
            # There is a conflict.
            # We need to provide the MergeConflictsFormSet with 'data'
            # for its fields AND 'choices' for the DynamicChoiceFormMixin.
            data, choices, total_forms = {}, {}, 0

            def add_prefix(key_name):
                return prefix + '-' + str(total_forms) + '-' + key_name

            for fld_name, values in sorted(self.updates.items()):
                if len(values) > 1:
                    # We do not care about values with len <= 1 do not
                    # cause merge conflicts (see _has_merge_conflicts).
                    model_field = self.opts.get_field(fld_name)
                    verbose_fld_name = model_field.verbose_name.capitalize()
                    data[add_prefix('original_fld_name')] = fld_name
                    data[add_prefix('verbose_fld_name')] = verbose_fld_name
                    choices[add_prefix('posvals')] = [(c, v) for c, v in enumerate(values)]
                    total_forms += 1

            management_form_data = {
                prefix + '-INITIAL_FORMS': '0',
                prefix + '-MAX_NUM_FORMS': '',
                prefix + '-TOTAL_FORMS': total_forms
            }
            data.update(management_form_data)
            kwargs['data'] = data
            # In order to pass 'choices' on to the individual forms of the
            # MergeConflictsFormSet, we need to wrap it in yet another dict
            # called 'form_kwargs'.
            # forms.BaseFormSet.__init__ will then do the rest for us.
            kwargs['form_kwargs'] = {'choices': choices}
        elif step == self.SELECT_PRIMARY_STEP:
            # MergeFormSelectPrimary form:
            # choices for the selection of primary are objects in the queryset
            # noinspection PyUnresolvedReferences
            kwargs['choices'] = {
                prefix + '-' + form_class.PRIMARY_FIELD_NAME: self.queryset
            }
        return kwargs

    def perform_action(self, *args: Any, **kwargs: Any) -> None:
        update_data = {}
        expand = self.get_cleaned_data_for_step('0').get('expand_primary', True)
        if expand:
            if self.get_cleaned_data_for_step('1'):
                # Conflicts were handled
                for form_data in self.get_cleaned_data_for_step('1'):
                    fld_name = form_data.get('original_fld_name')
                    value = self.updates[fld_name][int(form_data.get('posvals'))]
                    update_data[fld_name] = value
            for fld_name, value in self.updates.items():
                if fld_name not in update_data:
                    # This field was not part of conflict handling
                    if isinstance(value, (list, tuple)):
                        update_data[fld_name] = value[0]
                    else:
                        update_data[fld_name] = value
        original_pk = self.get_cleaned_data_for_step('0').get('primary', 0)
        primary = self.opts.model.objects.get(pk=original_pk)
        merge_records(
            primary, self.queryset, update_data, expand, request=self.request
        )

    def done(self, *args: Any, **kwargs: Any) -> None:
        """
        Perform the action.

        If the action fails due to a ProtectedError, send an admin message.
        """
        try:
            self.perform_action()
        except ProtectedError as e:
            # The merge could not be completed as there were protected objects
            # in the queryset, all changes were rolled back.
            # noinspection PyProtectedMember
            object_name = e.protected_objects.model._meta.verbose_name_plural
            if not object_name:  # pragma: no cover
                object_name = 'Objekte'
            msg_template = (
                "Folgende verwandte {object_name} verhinderten die "
                "Zusammenführung: {protected}"
            )
            self.model_admin.message_user(
                request=self.request,
                level=messages.ERROR,
                message=format_html(
                    msg_template,
                    object_name=object_name,
                    protected=link_list(self.request, e.protected_objects)
                )
            )
        return None


class MoveToBrochureBase(ActionConfirmationView):
    """Moves a set of ausgabe instances to a BaseBrochure child model."""

    short_description = 'zu Broschüren bewegen'
    template_name = 'admin/movetobrochure.html'
    action_name = 'moveto_brochure'
    allowed_permissions = ['moveto_brochure']
    action_allowed_checks = [check_same_magazin, '_check_protected_artikel', ]

    form_class = BrochureActionFormSet

    def get_initial(self):
        fields = (
            'pk', 'beschreibung', 'bemerkungen', 'magazin_id',
            'magazin__magazin_name', 'magazin_beschreibung'
        )
        values = (
            self.queryset
                .annotate(magazin_beschreibung=F('magazin__beschreibung'))
                .values_list(*fields)
        )
        initial = []
        for (pk, beschreibung, bemerkungen, magazin_id,
                magazin_name, magazin_beschreibung) in values:
            initial.append(
                {
                    'ausgabe_id': pk,
                    'titel': magazin_name,
                    'zusammenfassung': magazin_beschreibung,
                    'beschreibung': beschreibung,
                    'bemerkungen': bemerkungen,
                    'magazin_id': magazin_id
                }
            )
        return initial

    # noinspection PyAttributeOutsideInit
    @property
    def magazin_instance(self) -> Magazin:
        """Return the magazin instance common to all queryset objects."""
        # At this point the checks have run and excluded the possibility
        # that the queryset contains more than one magazin.
        if not hasattr(self, '_magazin_instance'):
            ausgabe_instance = self.queryset.select_related('magazin').first()
            if ausgabe_instance:
                self._magazin_instance = ausgabe_instance.magazin
            else:
                self._magazin_instance = None
        return self._magazin_instance

    # noinspection PyAttributeOutsideInit
    @property
    def can_delete_magazin(self) -> bool:
        """
        Assess if the magazin instance can be deleted following the action.
        """
        if not hasattr(self, '_can_delete_magazin'):
            if not self.magazin_instance:
                # This should be virtually impossible at this stage:
                # every ausgabe instance must have a magazin and django
                # enforces that at least one instance be selected from the
                # changelist to start an action.
                self._can_delete_magazin = False
            else:
                # Compare the set of all ausgabe instances of the magazin with
                # the set of the selected ausgaben.
                # If the sets match, all ausgabe instances of magazin will be
                # moved and the magazin will be open to deletion afterwards.
                # noinspection PyUnresolvedReferences
                magazin_ausgabe_set = set(
                    self.magazin_instance.ausgabe_set.values_list('pk', flat=True)
                )
                selected = set(
                    self.queryset.values_list('pk', flat=True)
                )
                self._can_delete_magazin = magazin_ausgabe_set == selected
        return self._can_delete_magazin

    # noinspection PyMethodParameters
    def _check_protected_artikel(view, **_kwargs: Any) -> bool:
        """Check whether any of the Artikel instances cannot be deleted."""
        ausgaben_with_artikel = (
            view.queryset
                .annotate(artikel_count=Count('artikel'))
                .filter(artikel_count__gt=0)
                .order_by('magazin')
        )
        if ausgaben_with_artikel.exists():
            msg_template = (
                'Aktion abgebrochen: Folgende Ausgaben besitzen '
                'Artikel, die nicht verschoben werden können: {} ({})'
            )
            view.model_admin.message_user(
                request=view.request,
                level=messages.ERROR,
                message=format_html(
                    msg_template,
                    link_list(view.request, ausgaben_with_artikel),
                    get_changelist_link(
                        model=_models.Ausgabe,
                        user=view.request.user,
                        obj_list=ausgaben_with_artikel,
                        blank=True
                    )
                )
            )
            return False
        return True

    def form_valid(self, form: Form) -> Optional[HttpResponse]:
        options_form = self.get_options_form(data=self.request.POST)
        if not options_form.is_valid():
            context = self.get_context_data(options_form=options_form)
            return self.render_to_response(context)
        self.perform_action(form.cleaned_data, options_form.cleaned_data)
        # Return to the changelist:
        return None

    def perform_action(  # type: ignore[override]
            self,
            form_cleaned_data: dict,
            options_form_cleaned_data: dict
    ) -> None:
        protected_ausg = []
        delete_magazin = options_form_cleaned_data.get('delete_magazin', False)
        # brochure_art is guaranteed to be a valid model name due to the
        # form validation.
        brochure_art = options_form_cleaned_data.get('brochure_art', '')
        brochure_class = get_model_from_string(brochure_art)

        for data in form_cleaned_data:
            if not data.get('accept', False):
                continue

            # Verify that the ausgabe exists and can be deleted
            # noinspection PyUnresolvedReferences
            try:
                ausgabe_instance = _models.Ausgabe.objects.get(
                    pk=data['ausgabe_id']
                )
            except (_models.Ausgabe.DoesNotExist, _models.Ausgabe.MultipleObjectsReturned):
                continue
            if is_protected([ausgabe_instance]):
                protected_ausg.append(ausgabe_instance)
                continue

            # Create the brochure object
            instance_data = {'titel': data['titel']}
            for key in ('zusammenfassung', 'beschreibung', 'bemerkungen'):
                if key in data and data[key]:
                    instance_data[key] = data[key]

            try:
                with transaction.atomic():
                    # noinspection PyUnresolvedReferences
                    new_brochure = brochure_class.objects.create(**instance_data)
                    # Update the bestand and delete the ausgabe
                    ausgabe_instance.bestand_set.update(
                        ausgabe_id=None, brochure_id=new_brochure.pk
                    )
                    ausgabejahre = ausgabe_instance.ausgabejahr_set.values_list(
                        'jahr', flat=True
                    )
                    for jahr in ausgabejahre:
                        _models.BrochureYear.objects.create(
                            brochure=new_brochure, jahr=jahr
                        )
                    log_deletion(self.request.user.pk, ausgabe_instance)
                    str_ausgabe = str(ausgabe_instance)
                    ausgabe_instance.delete()
            except ProtectedError:
                protected_ausg.append(ausgabe_instance)
            else:
                # noinspection PyProtectedMember,PyUnresolvedReferences
                create_logentry(
                    user_id=self.request.user.pk,
                    obj=new_brochure,
                    action_flag=ADDITION,
                    message="Hinweis: "
                            "{verbose_name} wurde automatisch erstellt beim Verschieben"
                            " von Ausgabe {str_ausgabe} (Magazin: {str_magazin}).".format(
                                verbose_name=brochure_class._meta.verbose_name,
                                str_ausgabe=str_ausgabe,
                                str_magazin=str(self.magazin_instance)
                            )
                )
                # Log the changes to the Bestand instances:
                qs = _models.Bestand.objects.filter(brochure_id=new_brochure.pk)
                for bestand_instance in qs:
                    log_change(
                        user_id=self.request.user.pk,
                        obj=bestand_instance,
                        fields=['ausgabe_id', 'brochure_id']
                    )
        # Notify the user about Ausgabe instances that could not be deleted and
        # return to the changelist - without deleting the Magazin instance
        # (since it will also be protected).
        if protected_ausg:
            msg_template = (
                "Folgende Ausgaben konnten nicht gelöscht werden: "
                "{obj_links} ({cl_link}). Es wurden keine Broschüren für "
                "diese Ausgaben erstellt."
            )
            self.model_admin.message_user(
                request=self.request,
                level=messages.ERROR,
                message=format_html(
                    msg_template,
                    obj_links=link_list(self.request, protected_ausg, blank=True),
                    cl_link=get_changelist_link(
                        model=_models.Ausgabe,
                        user=self.request.user,
                        obj_list=protected_ausg,
                        blank=True
                    )
                )
            )
            return None

        # The deletion should not interrupt/rollback the deletion of
        # the ausgabe, hence we do not include it in the ausgabe transaction.
        if delete_magazin:
            try:
                with transaction.atomic():
                    self.magazin_instance.delete()
            except ProtectedError:
                # Seems like the magazin was still protected after all.
                self.model_admin.message_user(
                    request=self.request,
                    level=messages.ERROR,
                    message=format_html(
                        "Magazin konnte nicht gelöscht werden: {}",
                        get_obj_link(
                            obj=self.magazin_instance, user=self.request.user, blank=True
                        )
                    )
                )
            else:
                log_deletion(self.request.user.pk, self.magazin_instance)

    def get_options_form(self, **kwargs: Any) -> Form:
        """Return the form that configures this action."""
        kwargs['can_delete_magazin'] = self.can_delete_magazin
        return BrochureActionFormOptions(**kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        formset = self.get_form()
        forms = []
        for form in formset:
            link = get_obj_link(
                obj=_models.Ausgabe.objects.get(pk=form['ausgabe_id'].initial),
                user=self.request.user,
                blank=True
            )
            forms.append((link, form))
        context['forms'] = forms
        context['management_form'] = formset.management_form
        context['options_form'] = self.get_options_form()
        context.update(kwargs)
        return context


class ChangeBestand(ConfirmationViewMixin, views.generic.TemplateView):
    """Edit the Bestand set of the parent model instance(s)."""

    template_name = 'admin/change_bestand.html'

    short_description = 'Bestände ändern'
    allowed_permissions = ['alter_bestand']

    action_name = 'change_bestand'
    action_reversible = True

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Optional[HttpResponse]:
        if 'action_confirmed' in request.POST:
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
        # Since we're not changing anything on the instance itself, an empty
        # model form will do.
        form = self.model_admin.get_form(
            self.request, obj=formset.instance, change=True
        )()
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

    def get_bestand_formset(
            self, request: HttpRequest, obj: Model
    ) -> Tuple[BaseInlineFormSet, InlineModelAdmin]:
        """Return the Bestand formset and model admin inline for this object."""
        formsets_with_inlines = self.model_admin.get_formsets_with_inlines(
            request, obj
        )
        for formset_class, inline in formsets_with_inlines:
            if inline.model == _models.Bestand:
                break
        else:
            raise ValueError(
                "Model admin '%s' has no inline for model Bestand!" % self.model_admin
            )
        formset_params = {
            'instance': obj,
            'prefix': "%s-%s" % (formset_class.get_default_prefix(), obj.pk),
            'queryset': inline.get_queryset(request),
        }
        if 'action_confirmed' in request.POST:
            formset_params['data'] = request.POST.copy()
        formset = formset_class(**formset_params)
        return formset, inline

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context['object_name'] = self.opts.object_name
        context['formsets'] = []
        media_updated = False
        for obj in self.queryset:
            formset, inline = self.get_bestand_formset(self.request, obj)
            # Wrap the formset into django's InlineAdminFormSet, so that we can
            # use django's edit_inline/tabular template.
            wrapped_formset = self.model_admin.get_inline_formsets(
                request=self.request,
                formsets=[formset],
                inline_instances=[inline],
                obj=obj
            )[0]
            if not media_updated:
                # Add the inline formset media (such as inlines.js):
                context['media'] += wrapped_formset.media
                media_updated = True
            context['formsets'].append(
                (
                    get_obj_link(obj=obj, user=self.request.user, blank=True),
                    wrapped_formset
                )
            )
        return context
