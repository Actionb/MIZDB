from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError, F, Count
from django.utils.html import format_html
from django.utils.translation import gettext_lazy, gettext

from DBentry import models as _models
from DBentry.actions.base import (
    ActionConfirmationView, WizardConfirmationView
)
from DBentry.actions.forms import (
    MergeFormSelectPrimary, MergeConflictsFormSet,
    BulkAddBestandForm, BulkEditJahrgangForm,
    BrochureActionFormSet, BrochureActionFormOptions
)
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.logging import LoggingMixin, log_addition
from DBentry.utils import (
    link_list, merge_records, get_updateable_fields, get_obj_link,
    get_changelist_link, get_model_from_string, is_protected
)


def check_same_magazin(view, **kwargs):
    """
    Check that all objects in the view's queryset are related to the same magazin.
    """
    if view.queryset.values('magazin_id').distinct().count() != 1:
        view.model_admin.message_user(
            request=view.request,
            level=messages.ERROR,
            message='Aktion abgebrochen: Die ausgewählten %s gehören zu '
            'unterschiedlichen Magazinen.' % view.opts.verbose_name_plural
        )
        return False


class BulkEditJahrgang(ActionConfirmationView, LoggingMixin):
    """
    View that bulk edits the jahrgang of a collection of ausgabe instances.
    """

    short_description = gettext_lazy("Add issue volume")
    allowed_permissions = ['change']
    action_name = 'bulk_jg'
    action_allowed_checks = [check_same_magazin]

    affected_fields = ['jahrgang', 'ausgabe_jahr__jahr']

    form_class = BulkEditJahrgangForm

    view_helptext = (
        "Sie können hier Jahrgänge zu den ausgewählten Ausgaben hinzufügen."
        "\nWählen Sie zunächst eine Schlüssel-Ausgabe, die den Beginn eines "
        "Jahrganges darstellt, aus und geben Sie den Jahrgang dieser Ausgabe an."
        "\nDie Jahrgangswerte der anderen Ausgaben werden danach in Abständen "
        "von einem Jahr (im Bezug zur Schlüssel-Ausgabe) hochgezählt, bzw. heruntergezählt."

        "\n\nAusgaben, die keine Jahresangaben besitzen (z.B. Sonderausgaben), "
        "werden ignoriert."
        "\nWird als Jahrgang '0' eingegeben, werden die Angaben für Jahrgänge "
        "aller ausgewählten Ausgaben gelöscht."
        "\nAlle bereits vorhandenen Angaben für Jahrgänge werden überschrieben."
    )

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['choices'] = {forms.ALL_FIELDS: self.queryset}
        return kwargs

    def get_initial(self):
        return {
            'jahrgang': 1,
            'start': self.queryset.values_list('pk', flat=True).first(),
        }

    def perform_action(self, form_cleaned_data):
        """
        Incrementally update the jahrgang for each instance.

        If the user has chosen the integer 0 for jahrgang,
        delete all jahrgang values instead.
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
        self.log_update(self.queryset, 'jahrgang')


class BulkAddBestand(ActionConfirmationView, LoggingMixin):
    """View that adds a bestand to a given model instances."""

    short_description = gettext_lazy("Alter stock")
    allowed_permissions = ['alter_bestand']
    action_name = 'add_bestand'

    affected_fields = ['bestand']

    form_class = BulkAddBestandForm

    view_helptext = (
        "Sie können hier Bestände für die ausgewählten Objekte hinzufügen."
        "\nBesitzt ein Objekt bereits einen Bestand in der ersten Kategorie "
        "('Lagerort (Bestand)'), so wird stattdessen diesem Objekt ein Bestand "
        "in der zweiten Kategorie ('Lagerort (Dublette)') hinzugefügt."
    )

    def get_initial(self):
        """Provide initial values for bestand and dublette fields."""
        if self.model == _models.ausgabe:
            try:
                return {
                    'bestand': _models.lagerort.objects.get(pk=ZRAUM_ID),
                    'dublette': _models.lagerort.objects.get(pk=DUPLETTEN_ID)
                }
            except _models.lagerort.DoesNotExist:
                pass
        return super().get_initial()

    def _build_message(self, lagerort_instance, bestand_instances, fkey):
        base_msg = ("{lagerort}-Bestand zu diesen {count} {verbose_model_name} "
            "hinzugefügt: {obj_links}")
        format_dict = {
            'verbose_model_name': self.opts.verbose_name_plural,
            'obj_links': link_list(
                request=self.request,
                obj_list=[getattr(obj, fkey.name) for obj in bestand_instances]
            ),
            'lagerort': str(lagerort_instance),
            'count': len(bestand_instances)
        }
        return format_html(base_msg, **format_dict)

    def _get_bestand_field(self, model):
        """Return the ForeignKey field from `bestand` to model `model`."""
        for field in _models.bestand._meta.get_fields():
            if field.is_relation and field.related_model == model:
                return field

    def perform_action(self, form_cleaned_data):
        """Add a bestand instance to the given instances."""

        bestand_lagerort = form_cleaned_data['bestand']
        dubletten_lagerort = form_cleaned_data['dublette']
        bestand_list = []
        dubletten_list = []
        # Get the correct fkey from bestand model to this view's model
        fkey = self._get_bestand_field(self.model)

        for instance in self.queryset:
            filter_kwargs = {fkey.name: instance, 'lagerort': bestand_lagerort}
            instance_data = {fkey.name: instance}
            if not _models.bestand.objects.filter(**filter_kwargs).exists():
                instance_data['lagerort'] = bestand_lagerort
                bestand_list.append(_models.bestand(**instance_data))
            else:
                instance_data['lagerort'] = dubletten_lagerort
                dubletten_list.append(_models.bestand(**instance_data))

        with transaction.atomic():
            for lagerort_instance, bestand_instances in (
                (bestand_lagerort, bestand_list),
                (dubletten_lagerort, dubletten_list)
            ):
                for obj in bestand_instances:
                    obj.save()
                    self.log_addition(getattr(obj, fkey.name), obj)
                admin_message = self._build_message(
                    lagerort_instance=lagerort_instance,
                    bestand_instances=bestand_instances,
                    fkey=fkey
                )
                self.model_admin.message_user(self.request, admin_message)


class MergeViewWizarded(WizardConfirmationView):
    """View that merges model instances.

    The user selects one instance from the available instances to designate
    it as the 'primary'.
    All other instances will be merged into that one instance.
    Optionally, the user can chose to expand the 'primary' with data from the
    other instances, for any fields of 'primary' that do not have a value.
    """

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

    # TODO: include this bit in the ACTUAL help page for this action:
    # Fehlen dem primären Datensatz Grunddaten und wird unten bei der
    # entsprechenden Option der Haken gesetzt, so werden die fehlenden Daten
    # nach Möglichkeit durch Daten aus den sekundären Datensätzen ergänzt.
    # Bereits bestehende Grunddaten des primären Datensatzes werden NICHT
    # überschrieben.
    step1_helptext = (
        "Bei der Zusammenfügung werden alle verwandten Objekte der"
        "zuvor in der Übersicht ausgewählten Datensätze dem primären"
        "Datensatz zugeteilt."
        "\nDanach werden die sekundären Datensätze GELÖSCHT."
    )
    step2_helptext = (
        "Für die Erweiterung der Grunddaten des primären Datensatzes stehen"
        "widersprüchliche Möglichkeiten zur Verfügung."
        "\nBitte wählen Sie jeweils eine der Möglichkeiten, die für den primären"
       " Datensatz übernommen werden sollen."
    )

    view_helptext = {
        SELECT_PRIMARY_STEP: step1_helptext,
        CONFLICT_RESOLUTION_STEP: step2_helptext
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the current step to the view's title.
        context['title'] = gettext(
            'Merge objects: step {}').format(str(int(self.steps.current) + 1))
        return context

    def _check_too_few_objects(view, **kwargs):
        if view.queryset.count() == 1:
            view.model_admin.message_user(
                request=view.request,
                level=messages.WARNING,
                message='Es müssen mindestens zwei Objekte aus der Liste '
                'ausgewählt werden, um diese Aktion durchzuführen.',
            )
            return False

    def _check_different_magazines(view, **kwargs):
        if (view.model == _models.ausgabe
                and view.queryset.values_list('magazin').distinct().count() > 1):
            # User is trying to merge ausgaben from different magazines.
            format_dict = {
                'self_plural': view.opts.verbose_name_plural,
                # Add a 'n' at the end because german grammar.
                'other_plural': _models.magazin._meta.verbose_name_plural + 'n'
            }
            view.model_admin.message_user(
                request=view.request,
                message=view.denied_message.format(**format_dict),
                level=messages.ERROR
            )
            return False

    def _check_different_ausgaben(view, **kwargs):
        if (view.model == _models.artikel
                and view.queryset.values('ausgabe').distinct().count() > 1):
            # User is trying to merge artikel from different ausgaben.
            format_dict = {
                'self_plural': view.opts.verbose_name_plural,
                'other_plural': _models.ausgabe._meta.verbose_name_plural
            }
            view.model_admin.message_user(
                request=view.request,
                message=view.denied_message.format(**format_dict),
                level=messages.ERROR
            )
            return False

    @property
    def updates(self):
        """Data to update the 'primary' instance with.

        Prepared by `_has_merge_conflicts` during processing the first step
        (SELECT_PRIMARY_STEP) and then added to the storage by `process_step`,
        this mapping of field_name: value contains the data to
        expand 'primary' with.
        """
        if not hasattr(self, '_updates'):
            step_data = self.storage.get_step_data(self.SELECT_PRIMARY_STEP)
            self._updates = step_data.get('updates', {})
        return self._updates

    def _has_merge_conflicts(self, data):
        """Determine if there is going to be a merge conflict.

        If the 'primary' is going to be expanded with values from the other
        instances and there is more than one possible value for any field,
        we have a conflict and the user needs to choose what value to keep.

        Parameters:
            data: the cleaned form data from step 0
                (i.e. the selection of the 'primary' instance).

        Returns:
            boolean: whether or not there is a conflict.
            dict: a dictionary of field_name: new_value for all the updates
                planned for 'primary'.
        """
        # Get the 'primary' object chosen by the user and
        # exclude it from the queryset we are working with.
        try:
            original_pk = data[self.get_form_prefix() + '-primary']
            primary = self.model.objects.get(pk=original_pk)
        except (KeyError, self.model.DoesNotExist):
            return False, None
        qs = self.queryset.exclude(pk=primary.pk)

        # get_updateable_fields() returns the fields that
        # may be updated by this merge;
        # i.e. empty fields without a (default) value.
        updateable_fields = get_updateable_fields(primary)
        if not updateable_fields:
            # No updates can be done on 'primary'.
            return False, None

        has_conflict = False
        # Keep track of fields of primary that would be updated.
        # If there is more than one possible change per field, we
        # need user input to decide what change to keep.
        # This is where then the next form MergeConflictsFormSet comes in.
        updates = {fld_name: set() for fld_name in updateable_fields}

        for other_record_valdict in qs.values(*updateable_fields):
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
        updates = {
            fld_name: list(value_set)
            for fld_name, value_set in updates.items()
            if value_set
        }
        return has_conflict, updates

    def process_step(self, form):
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
            # so that the conflict reslution will be skipped.
            self.storage.current_step = self.CONFLICT_RESOLUTION_STEP
        return data

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step is None:
            step = self.steps.current
        form_class = self.form_list[step]
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
                    choices[add_prefix('posvals')] = [
                        (c, v) for c, v in enumerate(values)
                    ]
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
            kwargs['choices'] = {
                prefix + '-' + form_class.PRIMARY_FIELD_NAME: self.queryset
            }
        return kwargs

    def perform_action(self, form_cleaned_data=None):
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
            primary, self.queryset, update_data, expand, request=self.request)

    def done(self, *args, **kwargs):
        try:
            self.perform_action()
        except ProtectedError as e:
            # The merge could not be completed as there were protected objects
            # in the queryset, all changes were rolled back.
            object_name = 'Objekte'
            msg_template = ("Folgende verwandte {object_name} verhinderten "
                "die Zusammenführung: {protected}")
            if e.protected_objects.model._meta.verbose_name_plural:
                object_name = e.protected_objects.model._meta.verbose_name_plural
            self.model_admin.message_user(
                request=self.request,
                level=messages.ERROR,
                message=format_html(
                    msg_template,
                    object_name=object_name,
                    protected=link_list(self.request, e.protected_objects)
                )
            )
        return


class MoveToBrochureBase(ActionConfirmationView, LoggingMixin):
    """Moves a set of ausgabe instances to a BaseBrochure child model."""

    short_description = 'zu Broschüren bewegen'
    template_name = 'admin/movetobrochure.html'
    action_name = 'moveto_brochure'
    allowed_permissions = ['delete']
    action_allowed_checks = [
        check_same_magazin,
        '_check_protected_artikel',
    ]

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
            initial.append({
                'ausgabe_id': pk,
                'titel': magazin_name,
                'zusammenfassung': magazin_beschreibung,
                'beschreibung': beschreibung,
                'bemerkungen': bemerkungen,
                'magazin_id': magazin_id
            })
        return initial

    @property
    def magazin_instance(self):
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

    @property
    def can_delete_magazin(self):
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
                magazin_ausgabe_set = set(
                    self.magazin_instance.ausgabe_set.values_list('pk', flat=True)
                )
                selected = set(
                    self.queryset.values_list('pk', flat=True)
                )
                self._can_delete_magazin = magazin_ausgabe_set == selected
        return self._can_delete_magazin

    def _check_protected_artikel(view, **kwargs):
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
                message= format_html(
                    msg_template,
                    link_list(view.request, ausgaben_with_artikel),
                    get_changelist_link(
                        model=_models.ausgabe,
                        user=view.request.user,
                        obj_list=ausgaben_with_artikel
                    )
                )
            )
            return False

    def form_valid(self, form):
        options_form = self.get_options_form(data=self.request.POST)
        if not options_form.is_valid():
            context = self.get_context_data(options_form=options_form)
            return self.render_to_response(context)
        self.perform_action(form.cleaned_data, options_form.cleaned_data)
        return

    def perform_action(self, form_cleaned_data, options_form_cleaned_data):
        protected_ausg = []
        delete_magazin = options_form_cleaned_data.get('delete_magazin', False)
        # brochure_art is guaranteed to be a valid
        # model name due to the form validation.
        brochure_art = options_form_cleaned_data.get('brochure_art', '')
        brochure_class = get_model_from_string(brochure_art)

        for data in form_cleaned_data:
            if not data.get('accept', False):
                continue

            # Verify that the ausgabe exists and can be deleted
            try:
                ausgabe_instance = _models.ausgabe.objects.get(
                    pk=data['ausgabe_id'])
            except (
                _models.ausgabe.DoesNotExist,
                _models.ausgabe.MultipleObjectsReturned):
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
                    new_brochure = brochure_class.objects.create(**instance_data)
                    # Update the bestand and delete the ausgabe
                    ausgabe_instance.bestand_set.update(
                        ausgabe_id=None, brochure_id=new_brochure.pk
                    )
                    ausgabe_jahre = ausgabe_instance.ausgabe_jahr_set.values_list(
                        'jahr', flat=True)
                    for jahr in ausgabe_jahre:
                        _models.BrochureYear.objects.create(
                            brochure=new_brochure, jahr=jahr
                        )
                    ausgabe_instance.delete()
            except ProtectedError:
                protected_ausg.append(ausgabe_instance)
            else:
                log_addition(
                    request=self.request,
                    object=new_brochure,
                    message="Hinweis: "
                    "{verbose_name} wurde automatisch erstellt beim Verschieben"
                    " von Ausgabe {str_ausgabe} (Magazin: {str_magazin}).".format(
                        verbose_name=brochure_class._meta.verbose_name,
                        str_ausgabe=str(ausgabe_instance),
                        str_magazin=str(self.magazin_instance)
                    )
                )
                self.log_update(
                    _models.bestand.objects.filter(brochure_id=new_brochure.pk),
                    ['ausgabe_id', 'brochure_id']
                )
                self.log_deletion(ausgabe_instance)

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
                    obj_links=link_list(self.request, protected_ausg),
                    cl_link=get_changelist_link(
                        model=_models.ausgabe,
                        user=self.request.user,
                        obj_list=protected_ausg
                    )
                )
            )
            return

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
                            obj=self.magazin_instance,
                            user=self.request.user,
                            include_name=False
                        )
                    )
                )
            else:
                self.log_deletion(self.magazin_instance)

    def get_options_form(self, **kwargs):
        kwargs['can_delete_magazin'] = self.can_delete_magazin
        return BrochureActionFormOptions(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = self.get_form()
        forms = []
        for form in formset:
            link = get_obj_link(
                obj=_models.ausgabe.objects.get(pk=form['ausgabe_id'].initial),
                user=self.request.user,
                include_name=False
            )
            forms.append((link, form))
        context['forms'] = forms
        context['management_form'] = formset.management_form
        context['options_form'] = self.get_options_form()
        context.update(kwargs)
        return context
