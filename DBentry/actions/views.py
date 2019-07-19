from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError, F, Count
from django.utils.html import format_html, mark_safe
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
    perm_required = ['change'] 
    action_name = 'bulk_jg'
    action_allowed_checks = [check_same_magazin]

    affected_fields = ['jahrgang', 'ausgabe_jahr__jahr']

    form_class = BulkEditJahrgangForm

    view_helptext = """ 
        Sie können hier Jahrgänge zu den ausgewählten Ausgaben hinzufügen.
        Wählen Sie zunächst eine Schlüssel-Ausgabe, die den Beginn eines Jahrganges darstellt, aus und geben Sie den Jahrgang dieser Ausgabe an.
        Die Jahrgangswerte der anderen Ausgaben werden danach in Abständen von einem Jahr (im Bezug zur Schlüssel-Ausgabe) hochgezählt, bzw. heruntergezählt.

        Ausgaben, die keine Jahresangaben besitzen (z.B. Sonderausgaben), werden ignoriert.
        Wird als Jahrgang '0' eingegeben, werden die Angaben für Jahrgänge aller ausgewählten Ausgaben gelöscht.
        Alle bereits vorhandenen Angaben für Jahrgänge werden überschrieben.
    """

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['choices'] = {forms.ALL_FIELDS: self.queryset}
        return kwargs

    def get_initial(self):
        return {
            'jahrgang': 1, 
            'start':self.queryset.values_list('pk', flat = True).first(), 
        }
        
    def perform_action(self, form_cleaned_data):
        """
        Incrementally update the jahrgang for each instance.

        If the user has chosen the integer 0 for jahrgang, 
        delete all jahrgang values instead.
        """
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data['jahrgang']
        start = self.queryset.get(pk = form_cleaned_data.get('start'))

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
    perm_required = ['alter_bestand']
    action_name = 'add_bestand'

    affected_fields = ['bestand']

    form_class = BulkAddBestandForm

    view_helptext = """ Sie können hier Bestände für die ausgewählten Objekte hinzufügen.
                        Besitzt ein Objekt bereits einen Bestand in der ersten Kategorie ('Lagerort (Bestand)'), so wird stattdessen diesem Objekt ein Bestand in der zweiten Kategorie ('Lagerort (Dublette)') hinzugefügt.
    """

    def get_initial(self):
        # get initial values for bestand and dublette based on the view's model
        if self.model == _models.ausgabe:
           return {
                'bestand' : _models.lagerort.objects.get(pk=ZRAUM_ID), 
                'dublette' : _models.lagerort.objects.get(pk=DUPLETTEN_ID)
            }
        return super().get_initial()

    def _build_message(self, lagerort_instance, bestand_instances, fkey):
        base_msg = "{lagerort}-Bestand zu diesen {count} {verbose_model_name} hinzugefügt: {obj_links}"
        format_dict = {
            'verbose_model_name': self.opts.verbose_name_plural, 
            'obj_links': link_list(
                request=self.request, 
                obj_list=[getattr(obj, fkey.name) for obj in bestand_instances]
            ), 
            'lagerort': str(lagerort_instance), 
            'count': len(bestand_instances)
        }
        return base_msg.format(**format_dict)

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
                    lagerort_instance = lagerort_instance, 
                    bestand_instances = bestand_instances, 
                    fkey = fkey
                )
                self.model_admin.message_user(self.request, admin_message)

class MergeViewWizarded(WizardConfirmationView): 
    """View that merges model instances.
    
    The user selects one instance from the available instances to designate
    it as the 'primary' or 'original'.
    All other instances will be merged into that one instance.
    Optionally, the user can chose to expand that 'original' with data from the
    other instances, for any fields of 'original' that do not have a value.
    """

    short_description = gettext_lazy("Merge selected %(verbose_name_plural)s")
    perm_required = ['merge']
    action_name = 'merge_records'
    action_allowed_checks = [
        '_check_too_few_objects', 
        '_check_different_magazines', 
        '_check_different_ausgaben'
    ]
    # Admin message for some failed checks.
    denied_message = 'Die ausgewählten {self_plural} gehören zu unterschiedlichen {other_plural}.'

    form_list = [MergeFormSelectPrimary, MergeConflictsFormSet] 

    _updates = {} 

    step1_helptext = """Bei der Zusammenfügung werden alle verwandten Objekte der zuvor in der Übersicht ausgewählten Datensätze dem primären Datensatz zugeteilt.
        Danach werden die sekundären Datensätze GELÖSCHT.
    """
    #TODO: include this bit in the ACTUAL help page for this action:
    #    Fehlen dem primären Datensatz Grunddaten und wird unten bei der entsprechenden Option der Haken gesetzt, so werden die fehlenden Daten nach Möglichkeit durch Daten aus den sekundären Datensätzen ergänzt.
    #   Bereits bestehende Grunddaten des primären Datensatzes werden NICHT überschrieben.

    step2_helptext = """Für die Erweiterung der Grunddaten des primären Datensatzes stehen widersprüchliche Möglichkeiten zur Verfügung.
        Bitte wählen Sie jeweils eine der Möglichkeiten, die für den primären Datensatz übernommen werden sollen.
    """

    view_helptext = {
        '0':step1_helptext, 
        '1':step2_helptext, 
    }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = gettext('Merge objects: step {}').format(str(int(self.steps.current)+1))
        return context
        
    def _check_too_few_objects(view, **kwargs):
        if view.queryset.count() == 1:
            view.model_admin.message_user(
                request = view.request, 
                level = messages.WARNING, 
                message = 'Es müssen mindestens zwei Objekte aus der Liste '
                'ausgewählt werden, um diese Aktion durchzuführen.', 
            )
            return False
            
    def _check_different_magazines(view, **kwargs):
        if (view.model == _models.ausgabe and
                view.queryset.values_list('magazin').distinct().count() > 1):
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
        if (view.model == _models.artikel and
                view.queryset.values('ausgabe').distinct().count() > 1):
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
        """Data to update the 'original' with.
        
        Prepared by `_has_merge_conflicts` during processing the first step (0)
        and then added to the storage by `process_step`, this mapping of
        field_name: value contains the data to expand 'original' with.
        """
        if not hasattr(self, '_updates'):
            step_data = self.storage.get_step_data('0') or {} 
            self._updates = step_data.get('updates', {}) 
        return self._updates 

    def process_step(self, form): 
        data = super().process_step(form) 
        if isinstance(form, MergeFormSelectPrimary): 
            has_conflict = False
            # There can only be conflicts if the original is meant to be expanded
            if form.cleaned_data.get('expand_o', False):
                prefix = self.get_form_prefix() 
                data = data.copy() # data is an instance of QueryDict and thus immutable - make it mutable by copying

                # Get the 'primary'/'original' object chosen by the user and exclude it from the queryset we are working with.
                original = self.opts.model.objects.get(pk=data.get(prefix + '-original', 0)) 
                qs = self.queryset.exclude(pk=original.pk)

                updateable_fields = get_updateable_fields(original) # The fields that may be updated by this merge 
                if updateable_fields: 
                    # Keep track of any fields of original that would be updated.
                    # If there is more than one possible change per field, we need user input to decide what change to keep.
                    # This is where MergeConflictsFormSet, the next form, comes in.
                    updates = { fld_name : set() for fld_name in updateable_fields}  

                    for other_record_valdict in qs.values(*updateable_fields): 
                        for k, v in other_record_valdict.items(): 
                            if v or isinstance(v, bool):
                                if len(updates[k])>0:
                                    # Another value for this field has already been found, we have found a conflict 
                                    has_conflict = True
                                # make v both hashable (for the set) and serializable (for the session)
                                updates[k].add(str(v)) 

                    # Sets are not JSON serializable, turn them into lists and remove empty ones 
                    updates = {fld_name:list(value_set) for fld_name, value_set in updates.items() if len(value_set)>0} 
                    data['updates'] = updates.copy() 
            if not has_conflict:
                # no conflict found, we can skip the MergeConflictsFormSet and continue
                #NOTE: this may break self.storage.set_step_files(self.steps.current, self.process_step_files(form)) - the next line - in post()
                self.storage.current_step = self.steps.last 
                # We use this way of skipping a form instead of declaring a condition_dict (the usual procedure for this WizardView),
                # as the process of finding the actual updates to make already involves looking for any conflicts.
        return data 

    def get_form_kwargs(self, step=None): 
        kwargs = super(MergeViewWizarded, self).get_form_kwargs(step) 
        if step is None: 
            step = self.steps.current 
        #TODO: do not rely on the existing order of forms to determine what form we are using
        # in a given step, maybe WizardView has some get_form_class_for_step method?
        if step == '1': 
            # If we are at step 1, then there is a conflict as two or more records are trying to change one of original's fields.
            # We need to provide the MergeConflictsFormSet with 'data' for its fields AND 'choices' for the DynamicChoiceFormMixin.
            form_class = self.form_list[step] 
            prefix = self.get_form_prefix(step, form_class) 
            data = { 
                    prefix + '-INITIAL_FORMS': '0', 
                    prefix + '-MAX_NUM_FORMS': '', 
            } 
            choices = {}
            #form_kwargs['form_kwargs'] = {'choices' : {}} 
            total_forms = 0 

            def add_prefix(key_name): 
                return prefix + '-' + str(total_forms) + '-' + key_name 

            for fld_name, values in sorted(self.updates.items()): 
                if len(values)>1: 
                    # We do not care about values with len <= 1 as these do not cause merge conflicts (see process_step) 
                    data.update({ 
                        add_prefix('original_fld_name') : fld_name,  
                        add_prefix('verbose_fld_name') : self.opts.get_field(fld_name).verbose_name.capitalize(),  
                    })
                    choices.update({ add_prefix('posvals') : [(c, v) for c, v in enumerate(values)]}) 
                    total_forms += 1

            data[prefix + '-TOTAL_FORMS'] = total_forms 
            kwargs['data'] = data
            # In order to pass 'choices' on to the individual forms of the MergeConflictsFormSet, 
            # we need to wrap it in yet another dict called 'form_kwargs'.
            # forms.BaseFormSet.__init__ will then do the rest for us.
            kwargs['form_kwargs'] = {'choices':choices}
        else: 
            # MergeFormSelectPrimary form: choices for the selection of primary are objects in the queryset
            kwargs['choices'] = {forms.ALL_FIELDS: self.queryset}
            # TODO: replace ALL_FIELDS with the 'original' formfield 
            #(make the reference to it an attribute on the form?)
        return kwargs 

    def perform_action(self, form_cleaned_data = None): 
        update_data = {} 
        expand = self.get_cleaned_data_for_step('0').get('expand_o', True) 
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
        original_pk = self.get_cleaned_data_for_step('0').get('original', 0) 
        original = self.opts.model.objects.get(pk=original_pk) 
        merge_records(original, self.queryset, update_data, expand, request=self.request)

    def done(self, *args, **kwargs):
        try:
            self.perform_action()
        except ProtectedError as e:
            # The merge could not be completed as there were protected objects in the queryset, all changes were rolled back
            protected = format_html(link_list(self.request, e.protected_objects))
            object_name = e.protected_objects.model._meta.verbose_name_plural or 'Objekte' 
            msg = gettext('Folgende verwandte {object_name} verhinderten die Zusammenführung: ').format(object_name=object_name) + protected
            self.model_admin.message_user(self.request, format_html(msg), 'error')
        return None

class MoveToBrochureBase(ActionConfirmationView, LoggingMixin):

    short_description = 'zu Broschüren bewegen'
    template_name = 'admin/movetobrochure.html'
    action_name = 'moveto_brochure'
    action_allowed_checks = [
        check_same_magazin, 
        '_check_protected_artikel', 
    ]
    # NOTE: MoveToBrochureBase does not declare 'perm_required'

    form_class = BrochureActionFormSet

    def get_initial(self):
        fields = ('pk', 'beschreibung', 'bemerkungen', 'magazin_id', 'magazin__magazin_name', 'magazin_beschreibung')
        values = self.queryset.annotate(magazin_beschreibung = F('magazin__beschreibung')).values_list(*fields)
        return [
            {
                'ausgabe_id': pk, 
                'titel': magazin_name, 
                'zusammenfassung': magazin_beschreibung, 
                'beschreibung': beschreibung, 
                'bemerkungen': bemerkungen, 
                'magazin_id': magazin_id
            }
                for pk, beschreibung, bemerkungen, magazin_id, magazin_name, magazin_beschreibung in values
        ]
        
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
                magazin_ausgabe_set = set(self.magazin_instance.ausgabe_set.values_list('pk', flat=True))
                selected_ausgabe_set = set(self.queryset.values_list('pk', flat=True))
                self._can_delete_magazin = magazin_ausgabe_set == selected_ausgabe_set
        return self._can_delete_magazin
        
    def _check_protected_artikel(view, **kwargs):
        ausgaben_with_artikel = view.queryset.annotate(artikel_count = Count('artikel')).filter(artikel_count__gt=0).order_by('magazin')
        if ausgaben_with_artikel.exists():
            msg_text = "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht verschoben werden können: {} ({})"
            msg_text = msg_text.format(
                link_list(view.request, ausgaben_with_artikel), 
                get_changelist_link(_models.ausgabe, view.request.user, obj_list = ausgaben_with_artikel)
                )
            view.model_admin.message_user(view.request, msg_text, messages.ERROR)
            return False

    def form_valid(self, form):
        options_form = self.get_options_form(data = self.request.POST)
        if not options_form.is_valid():
            context = self.get_context_data(options_form = options_form)
            return self.render_to_response(context)
        self.perform_action(form.cleaned_data, options_form.cleaned_data)
        return

    def perform_action(self, form_cleaned_data, options_form_cleaned_data):               
        protected_ausg = []        
        delete_magazin = options_form_cleaned_data.get('delete_magazin', False)
        # brochure_art is guaranteed to be a valid model name due to the form validation.
        brochure_class = get_model_from_string(options_form_cleaned_data.get('brochure_art', ''))

        for data in form_cleaned_data:
            if not data.get('accept', False):
                continue

            # Verify that the ausgabe exists and can be deleted
            ausgabe_instance = _models.ausgabe.objects.filter(pk=data['ausgabe_id']).first()
            if ausgabe_instance is None:
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
                    ausgabe_instance.bestand_set.update(ausgabe_id=None, brochure_id=new_brochure.pk)
                    ausgabe_jahre = ausgabe_instance.ausgabe_jahr_set.values_list('jahr', flat=True)
                    for jahr in ausgabe_jahre:
                        _models.BrochureYear.objects.create(brochure = new_brochure, jahr = jahr)
                    ausgabe_instance.delete()
            except ProtectedError:
                protected_ausg.append(ausgabe_instance)
            else:
                hint = "Hinweis: {verbose_name} wurde automatisch erstellt beim Verschieben von Ausgabe {str_ausgabe} (Magazin: {str_magazin})."
                changelog_message = hint.format(
                    verbose_name = brochure_class._meta.verbose_name, 
                    str_ausgabe = str(ausgabe_instance), str_magazin = str(self.magazin_instance)
                )
                log_addition(request = self.request, object = new_brochure, message = changelog_message)
                self.log_update(_models.bestand.objects.filter(brochure_id=new_brochure.pk), ['ausgabe_id', 'brochure_id'])
                self.log_deletion(ausgabe_instance)

        if protected_ausg:
            msg = "Folgende Ausgaben konnten nicht gelöscht werden: " + link_list(self.request, protected_ausg) \
                + ' (%s)' % get_changelist_link(_models.ausgabe, self.request.user, obj_list = protected_ausg)
            msg += ". Es wurden keine Broschüren für diese Ausgaben erstellt."
            self.model_admin.message_user(self.request, mark_safe(msg), 'error')
            return

        # The deletion should not interrupt/rollback the deletion of the ausgabe, hence we do not include it in the ausgabe transaction
        if delete_magazin:
                try:
                    with transaction.atomic():
                        self.magazin_instance.delete()
                except ProtectedError:
                    # Seems like the magazin was still protected after all. 
                    msg = "Magazin konnte nicht gelöscht werden: " + get_obj_link(self.magazin_instance, self.request.user, include_name = False)
                    self.model_admin.message_user(self.request, mark_safe(msg), 'error')
                else:
                    self.log_deletion(self.magazin_instance)

    def get_options_form(self, **kwargs):
        kwargs['can_delete_magazin'] = self.can_delete_magazin
        return BrochureActionFormOptions(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = self.get_form()
        context['management_form'] = formset.management_form
        context['forms'] = [
            (
                get_obj_link(_models.ausgabe.objects.get(pk=form['ausgabe_id'].initial), self.request.user, include_name = False), 
                form
            )
            for form in formset
        ]
        context['options_form'] = self.get_options_form()
        context.update(kwargs)
        return context
