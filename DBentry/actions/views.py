
from django.db import transaction
from django.db.models import ProtectedError
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy, gettext
from django.contrib.admin.utils import get_fields_from_path

from DBentry.utils import link_list, merge_records, get_updateable_fields, get_obj_link, get_model_from_string, is_protected
from DBentry.models import ausgabe, magazin, artikel, bestand, lagerort, BrochureYear
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.logging import LoggingMixin

from .base import ActionConfirmationView, WizardConfirmationView
from .forms import BulkAddBestandForm, MergeFormSelectPrimary, MergeConflictsFormSet, BulkEditJahrgangForm, BrochureActionFormSet
    
class BulkEditJahrgang(ActionConfirmationView, LoggingMixin):
    
    short_description = gettext_lazy("Add issue volume")
    perm_required = ['change']
    action_name = 'bulk_jg'
    
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
        kwargs['choices'] = self.queryset
        return kwargs
        
    def get_initial(self):
        return {
            'jahrgang': 1, 
            'start':self.queryset.values_list('pk', flat = True).first(), 
        }
    
    def action_allowed(self):
        if self.queryset.values('magazin_id').distinct().count() != 1:
            msg_text = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
            self.model_admin.message_user(self.request, msg_text, 'error')
            return False
        return True
    
    def perform_action(self, form_cleaned_data):
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data['jahrgang']
        start = self.queryset.get(pk = form_cleaned_data.get('start'))
        
        if jg == 0:
            # User entered 0 for jahrgang. Delete jahrgang data from the selected ausgaben.
            qs.update(jahrgang=None)
        else:
            qs.increment_jahrgang(start, jg)
        self.log_update(self.queryset, 'jahrgang')
                
                
class BulkAddBestand(ActionConfirmationView, LoggingMixin):

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
        initial = super().get_initial()
        if self.model == ausgabe:
            initial = {'bestand' : lagerort.objects.get(pk=ZRAUM_ID), 'dublette' : lagerort.objects.get(pk=DUPLETTEN_ID)}
        return initial
       
    def perform_action(self, form_cleaned_data):
        
        base_msg = "{lagerort}-Bestand zu diesen {count} {verbose_model_name} hinzugefügt: {obj_links}"
        format_dict = {'verbose_model_name':self.opts.verbose_name_plural}
        
        bestand_lagerort = form_cleaned_data['bestand']
        dupletten_lagerort = form_cleaned_data['dublette']
        
        bestand_list = []
        dubletten_list = []
        # Get the correct fkey from bestand model to this view's model
        fkey = get_fields_from_path(self.opts.model, 'bestand')[0].field
        
        for instance in self.queryset:
            if not bestand.objects.filter(**{fkey.name:instance, 'lagerort':bestand_lagerort}):
                bestand_list.append(bestand(**{fkey.name:instance, 'lagerort':bestand_lagerort}))
            else:
                dubletten_list.append(bestand(**{fkey.name:instance, 'lagerort':dupletten_lagerort}))
                
        with transaction.atomic():
            if bestand_list:
                for obj in bestand_list:
                    obj.save()
                    self.log_addition(getattr(obj, fkey.name), obj)
                #bestand.objects.bulk_create(bestand_list)
                obj_links = link_list(self.request, [getattr(z, fkey.name) for z in bestand_list])
                format_dict.update({'lagerort': str(bestand_lagerort), 'count':len(bestand_list), 'obj_links': obj_links})
                msg_text = base_msg.format(**format_dict)
                self.model_admin.message_user(self.request, format_html(msg_text))
            
            if dubletten_list:
                for obj in dubletten_list:
                    obj.save()
                    self.log_addition(getattr(obj, fkey.name), obj)
                #bestand.objects.bulk_create(dubletten_list)
                obj_links = link_list(self.request, [getattr(z, fkey.name) for z in dubletten_list])
                format_dict.update({'lagerort': str(dupletten_lagerort), 'count':len(dubletten_list), 'obj_links': obj_links})
                msg_text = base_msg.format(**format_dict)
                self.model_admin.message_user(self.request, format_html(msg_text))
 
class MergeViewWizarded(WizardConfirmationView): 
    
    short_description = gettext_lazy("Merge selected %(verbose_name_plural)s")
    perm_required = ['merge']
    action_name = 'merge_records'
     
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
    
    def action_allowed(self):
        model = self.opts.model
        request = self.request
        queryset = self.queryset
        
        MERGE_DENIED_MSG = 'Die ausgewählten {} gehören zu unterschiedlichen {}{}.'
        
        if queryset.count()==1:
            msg_text = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.' 
            self.model_admin.message_user(request, msg_text, 'warning')
            return False
        if model == ausgabe and queryset.values_list('magazin').distinct().count()>1:
            # User is trying to merge ausgaben from different magazines
            self.model_admin.message_user(request, MERGE_DENIED_MSG.format(self.opts.verbose_name_plural, magazin._meta.verbose_name_plural, 'n'), 'error')
            return False
        if model == artikel and self.queryset.values('ausgabe').distinct().count()>1:
            # User is trying to merge artikel from different ausgaben
            self.model_admin.message_user(request, MERGE_DENIED_MSG.format(self.opts.verbose_name_plural, ausgabe._meta.verbose_name_plural, ''), 'error')
            return False
        return True
         
    @property 
    def updates(self): 
        if not self._updates: 
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
        if step == '1': 
            # If we are at step 1, then there is a conflict as two or more records are trying to change one of original's fields.
            # We need to provide the MergeConflictsFormSet with 'data' for its fields AND 'choices' for the DynamicChoiceForm.
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
            kwargs['choices'] = self.queryset 
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
    
    form_class = BrochureActionFormSet
    
    def get_initial(self):
        return [
            {
                'ausgabe_id': pk, 'titel': beschreibung, 'bemerkungen': bemerkungen, 'magazin_id': magazin_id
            }
                for pk, beschreibung, bemerkungen, magazin_id in self.queryset.values_list('pk', 'beschreibung', 'bemerkungen', 'magazin_id')
        ]
        
    def get_form_kwargs(self):
        # Pass a dictionary with index, boolean whether delete_magazin should be disabled for the form with that index.
        # This could possibly also live in the formset class BrochureActionFormSet
        kwargs = super().get_form_kwargs()
        cannot_delete_mags = [
            mag.pk
            for mag in magazin.objects.filter(pk__in=self.queryset.values_list('magazin_id', flat = True))
            if list(mag.ausgabe_set.order_by('pk').values_list('pk', flat = True)) != list(self.queryset.order_by('pk').filter(magazin_id=mag.pk).values_list('pk', flat = True))
        ]
        kwargs['disables'] = {
            index: init_kwargs['magazin_id'] in cannot_delete_mags
            for index, init_kwargs in enumerate(kwargs['initial'])
        }
        return kwargs
        
    def action_allowed(self):
        from django.db.models import Count
        ausgaben_with_artikel = self.queryset.annotate(artikel_count = Count('artikel')).filter(artikel_count__gt=0)
        if ausgaben_with_artikel.exists():
            msg_text = "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht verschoben werden können: {}"
            msg_text = msg_text.format(link_list(self.request, ausgaben_with_artikel))
            self.model_admin.message_user(self.request, mark_safe(msg_text), 'error')
            return False
        return True
        
    def perform_action(self, form_cleaned_data = None):        
        protected_ausg, protected_mags = [], []
        
        for data in form_cleaned_data:
            if not data.get('accept', False):
                continue
            
            # Verify that the ausgabe exists and can be deleted
            ausgabe_instance = ausgabe.objects.filter(pk=data['ausgabe_id']).first()
            if ausgabe_instance is None:
                continue
            if is_protected([ausgabe_instance]):
                protected_ausg.append(ausgabe_instance)
                continue
            magazin_instance = ausgabe_instance.magazin
            
            # Create the brochure object
            brochure_class = get_model_from_string(data.get('brochure_art', ''))
            if brochure_class is None:
                continue
            instance_data = {'titel': data['titel']}
            for key in ('zusammenfassung', 'beschreibung', 'bemerkungen'):
                if key in data and data[key]:
                    instance_data[key] = data[key]
                    
            # Add a hint to bemerkungen how this brochure was created
            if not 'bemerkungen' in instance_data:
                instance_data['bemerkungen'] = ''
            hint = "Hinweis: {verbose_name} wurde automatisch erstellt beim Verschieben von Ausgabe {str_ausgabe} (Magazin: {str_magazin})."
            instance_data['bemerkungen'] += hint.format(
                verbose_name = brochure_class._meta.verbose_name, 
                str_ausgabe = str(ausgabe_instance), str_magazin = str(magazin_instance)
            )
            
            try:
                with transaction.atomic():
                    new_brochure = brochure_class.objects.create(**instance_data) 
                    # Update the bestand and delete the ausgabe
                    ausgabe_instance.bestand_set.update(ausgabe_id=None, brochure_id=new_brochure.pk)
                    ausgabe_jahre = ausgabe_instance.ausgabe_jahr_set.values_list('jahr', flat=True)
                    for jahr in ausgabe_jahre:
                        BrochureYear.objects.create(brochure = new_brochure, jahr = jahr)
                    ausgabe_instance.delete()
            finally:
                self.log_addition(new_brochure)
                self.log_update(bestand.objects.filter(brochure_id=new_brochure.pk), ['ausgabe_id', 'brochure_id'])
                self.log_deletion(ausgabe_instance)
                
            # The deletion should not interrupt/rollback the deletion of the ausgabe, hence we do not include it in the ausgabe transaction
            if data.get('delete_magazin', False):
                if is_protected([magazin_instance]):
                    protected_mags.append(magazin_instance)
                else:
                    try:
                        with transaction.atomic():
                            magazin_instance.delete()
                    finally:
                        self.log_deletion(magazin_instance)
                    
        if protected_ausg:
            msg = "Folgende Ausgaben konnten nicht gelöscht werden: " + link_list(self.request, protected_ausg)
            msg += ". Es wurden keine Broschüren für diese Ausgaben erstellt."
            self.model_admin.message_user(self.request, mark_safe(msg), 'error')
            
        if protected_mags:
            msg = "Folgende Magazine konnten nicht gelöscht werden: " + link_list(self.request, protected_mags)
            self.model_admin.message_user(self.request, mark_safe(msg), 'error')
            
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = self.get_form()
        context['management_form'] = formset.management_form
        context['forms'] = [
            (
                get_obj_link(ausgabe.objects.get(pk=form['ausgabe_id'].initial), self.request.user, include_name = False), 
                form
            )
            for form in formset
        ]
        return context
