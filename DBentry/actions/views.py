
from django.db import transaction
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib.admin.utils import get_fields_from_path

from DBentry.utils import link_list, merge_records
from DBentry.models import *
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.logging import LoggingMixin

from .base import ActionConfirmationView, WizardConfirmationView
from .forms import BulkAddBestandForm, MergeFormSelectPrimary, MergeConflictsFormSet

    
class BulkEditJahrgang(ActionConfirmationView, LoggingMixin):
    
    short_description = _("Add issue volume")
    perm_required = ['change']
    action_name = 'bulk_jg'
    
    affected_fields = ['jahrgang', 'ausgabe_jahr__jahr']
    
    initial = {'jahrgang':1}
    fields = ['jahrgang']
    help_texts = {'jahrgang':'Wählen sie den Jahrgang für das erste Jahr.'}
    
    view_helptext = """ Sie können hier Jahrgänge zu den ausgewählten Ausgaben hinzufügen.
                        Dabei wird das früheste Jahr in der Auswahl als Startpunkt aufgefasst und der Wert für den Jahrgang für jedes weitere Jahr entsprechend hochgezählt.
                        Für Ausgaben, die keine Jahresangaben besitzen (z.B. Sonderausgaben), wird nur der eingegebene Wert für den Jahrgang benutzt.
                        Wird als Jahrgang 0 eingegeben, werden die Angaben für Jahrgänge der ausgewählten Ausgaben gelöscht.
                        Alle bereits vorhandenen Angaben für Jahrgänge werden überschrieben.
    """
    
    def action_allowed(self):
        if self.queryset.values('magazin_id').distinct().count() != 1:
            msg_text = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
            self.model_admin.message_user(self.request, msg_text, 'error')
            return False
        return True
    
    def perform_action(self, form_cleaned_data):
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data['jahrgang']
        if jg == 0:
            # User entered 0 for jahrgang. Delete jahrgang data from the selected ausgaben.
            qs.update(jahrgang=None)
        else:
            years_in_qs = qs.values_list('ausgabe_jahr__jahr', flat = True).exclude(ausgabe_jahr__jahr=None).order_by('ausgabe_jahr__jahr').distinct()
            previous_year = years_in_qs.first()
            with transaction.atomic():            
                # Update all the objects that do not have a year
                qs.filter(ausgabe_jahr__jahr=None).update(jahrgang=jg)
                
                # Update all the objects that do have a year, and increment the jahrgang accordingly
                for year in years_in_qs:
                    jg += year - previous_year
                    loop_qs = qs.filter(ausgabe_jahr__jahr=year)
                    loop_qs.update(jahrgang=jg)
                    # Do not update the same issue twice (e.g. issues with two years)
                    qs = qs.exclude(ausgabe_jahr__jahr=year)
                    previous_year = year
        self.log_update(self.queryset, 'jahrgang')
                
                
class BulkAddBestand(ActionConfirmationView, LoggingMixin):

    short_description = _("Alter stock")
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
    
    short_description = ugettext_lazy("Merge selected %(verbose_name_plural)s")
    perm_required = ['merge']
    action_name = 'merge_records'
     
    form_list = [MergeFormSelectPrimary, MergeConflictsFormSet] 
     
    _updates = {} 
    
    #TODO: translation
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
        context['title'] = ugettext_lazy('Merge objects step: {}'.format(str(int(self.steps.current)+1)))
        return context
    
    def action_allowed(self):
        model = self.opts.model
        request = self.request
        queryset = self.queryset
        
        MERGE_DENIED_MSG = 'Die ausgewählten {} gehören zu unterschiedlichen {}{}.' #TODO: translation
        
        if queryset.count()==1:
            msg_text = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.' #TODO: translation
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
        data = super(MergeViewWizarded, self).process_step(form) 
        if isinstance(form, MergeFormSelectPrimary): 
            has_conflict = False
            # There can only be conflicts if the original is meant to be expanded
            if form.cleaned_data.get('expand_o', False):
                prefix = self.get_form_prefix() 
                data = data.copy() # data is an instance of QueryDict and thus immutable - make it mutable by copying
                
                # Get the 'primary'/'original' object chosen by the user and exclude it from the queryset we are working with.
                original = self.opts.model.objects.get(pk=data.get(prefix + '-original', 0)) 
                qs = self.queryset.exclude(pk=original.pk)
                
                updateable_fields = original.get_updateable_fields() # The fields that may be updated by this merge 
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
                                #NOTE: str() everything? What about boolean or lists?
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
         
