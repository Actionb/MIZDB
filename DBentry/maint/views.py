
from django.shortcuts import render, redirect 
from django.http import HttpResponse 
 
from django.urls import reverse_lazy, reverse 
from django.db.models import Count 
from django.apps import apps 
from django.views.generic import FormView 
 
from itertools import chain 
 
from DBentry.views import MIZAdminView, MIZSessionWizardView 
from DBentry.admin import miz_site 
from DBentry.models import * 
 
from .forms import * 
 
class MaintView(MIZAdminView): 
    url_name = 'maint_main' 
    index_label = 'Wartung' 
    template_name = 'admin/basic.html' 
    success_url = reverse_lazy('admin:index') 
     
    @classmethod 
    def has_permission(cls, request): 
        return request.user.is_superuser 
     
     
class UnusedObjectsView(MaintView): 
    model_name = '' 
    lte = 0 
     
    def get(self, request, *args, **kwargs): 
        lte = self.kwargs.get('lte', self.lte) 
        model_name = self.kwargs.get('model', self.model_name) 
        url = reverse('admin:DBentry_{}_changelist'.format(model_name)) 
        model = apps.get_model('DBentry', model_name) 
        qs = model.objects.annotate(num_a=Count('artikel')).filter(num_a__lte=lte) 
        request.session['qs'] = dict(id__in=list(qs.values_list('pk', flat=True))) 
        return redirect(url) 
         
miz_site.register_tool(MaintView) 
 
def has_change_conflict(wizard): 
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {} 
    if not cleaned_data: 
        # Don't think this can happen. To get to this step, it is required to have posted a valid form in the 0-th step. 
        return False 
    if not cleaned_data.get('expand_o'): 
        # Original is not meant to be expanded, there cannot be any conflicts 
        return False 
    original_pk = cleaned_data.get('original', 0) 
    original = wizard.model.objects.get(pk=original_pk) 
    qs = wizard.qs.exclude(pk=original_pk) 
    has_conflict = False 
     
    original_valdict = wizard.model.objects.filter(pk=original.pk).values()[0] 
    # The fields that may be updated by this merge 
    updateable_fields = original.get_updateable_fields() 
    if updateable_fields: 
        # Keep track of any fields or original that would be updated (needs user input to decide what change to keep if more than one) 
        updates = { fld_name : [] for fld_name in updateable_fields}  
         
        for other_record_valdict in qs.values(*updateable_fields): 
            for k, v in other_record_valdict.items(): 
                if v: 
                    if updates[k]: 
                        # Another value for this field has already been found, we have found a conflict 
                        return True 
                    else: 
                        updates[k].append(v) 
    return False 
     
 
class MergeViewWizarded(MIZSessionWizardView): 
     
    form_list = [MergeFormSelectPrimary, MergeConflictsFormSet] 
    template_name = 'admin/basic_wizard.html' 
    condition_dict = { 
        '1' : has_change_conflict 
    } 
     
    _updates = {} 
     
    @property 
    def updates(self): 
        if not self._updates: 
            step_data = self.storage.get_step_data('0') or {} 
            self._updates = step_data.get('updates', {}) 
        return self._updates 
         
    def process_step(self, form): 
        data = super(MergeViewWizarded, self).process_step(form) 
        if isinstance(form, MergeFormSelectPrimary): 
            prefix = self.get_form_prefix() 
            data = data.copy() 
            original = self.model.objects.get(pk=data.get(prefix + '-original', 0)) 
            qs = self.qs.exclude(pk=original.pk) #NOTE: set self.qs = qs.exclude here ? 
             
            original_valdict = self.model.objects.filter(pk=original.pk).values()[0] 
            # The fields that may be updated by this merge 
            #updateable_fields = [k for k, v in original_valdict.items() if v == '' or v is None]  
            updateable_fields = original.get_updateable_fields() 
            if updateable_fields: 
                # Keep track of any fields or original that would be updated (needs user input to decide what change to keep if more than one) 
                updates = { fld_name : set() for fld_name in updateable_fields}  
                 
                for other_record_valdict in qs.values(*updateable_fields): 
                    for k, v in other_record_valdict.items(): 
                        if v: 
                            updates[k].add(str(v)) 
                             
                # Sets are not JSON serializable, turn them into lists and remove empty ones 
                updates = {k:list(v) for k, v in updates.items() if v} 
                data['updates'] = updates.copy() 
        return data 
     
    def dispatch(self, request, *args, **kwargs): 
        # Set self.model, etc. now - dispatch is the next method after as_view() in which self.kwargs is set  
        # (self.kwargs does not yet exist during initilization) 
        self.model = apps.get_model('DBentry', self.kwargs.get('model_name')) 
        self.opts = self.model._meta 
        self.ids = self.request.session.get('merge').get('qs_ids') 
        self.qs = self.model.objects.filter(id__in=self.ids) 
        self.success_url = self.request.session.get('merge').get('success_url',  
                                reverse_lazy('admin:DBentry_{}_changelist'.format(self.model._meta.model_name)) 
                            ) 
        return super(MergeViewWizarded, self).dispatch(request, *args, **kwargs) 
         
    def get_form_kwargs(self, step=None): 
        form_kwargs = super(MergeViewWizarded, self).get_form_kwargs(step) 
        if step is None: 
            step = self.steps.current 
        if step == '1': 
            # There is a conflict as two or more records are trying to change one of original's fields 
            form_class = self.form_list[step] 
            prefix = self.get_form_prefix(step, form_class) 
            form_kwargs['form_kwargs'] = {'choices' : {}} 
            total_forms = 0 
            def add_prefix(key_name): 
                return prefix + '-' + str(total_forms) + '-' + key_name 
            for fld_name, values in sorted(self.updates.items()): 
                if len(values)>1: 
                    form_kwargs['form_kwargs']['choices'].update({ add_prefix('posvals') : [(c, v) for c, v in enumerate(values)]}) 
                    total_forms += 1 
        else: 
            form_kwargs['choices'] = self.qs 
        return form_kwargs 
             
    def get_form_data(self, step=None): 
        if step == '1': 
            # There is a conflict as two or more records are trying to change one of original's fields 
            form_class = self.form_list[step] 
            prefix = self.get_form_prefix(step, form_class) 
            form_data = { 
                    prefix + '-INITIAL_FORMS': '0', 
                    prefix + '-MAX_NUM_FORMS': '', 
                } 
            total_forms = 0 
             
            def add_prefix(key_name): 
                return prefix + '-' + str(total_forms) + '-' + key_name 
            for fld_name, values in sorted(self.updates.items()): 
                if len(values)>1: 
                    data = { 
                        add_prefix('original_fld_name') : fld_name,  
                        add_prefix('verbose_fld_name') : self.opts.get_field(fld_name).verbose_name,  
                    } 
                    form_data.update(data) 
                    total_forms += 1 
                     
            form_data[prefix + '-TOTAL_FORMS'] = total_forms 
            return form_data 
         
    def get_form(self, step=None, data=None, files=None): 
        """ 
        Constructs the form for a given `step`. If no `step` is defined, the 
        current step will be determined automatically. 
 
        The form will be initialized using the `data` argument to prefill the 
        new form. If needed, instance or queryset (for `ModelForm` or 
        `ModelFormSet`) will be added too. 
        """ 
        if step is None: 
            step = self.steps.current 
        if step != '1': 
            return super(MergeViewWizarded, self).get_form(step, data, files) 
        form_class = self.form_list[step] 
        # prepare the kwargs for the form instance. 
        kwargs = self.get_form_kwargs(step) 
        kwargs.update({ 
            'data': data or self.get_form_data(step), 
            'files': files, 
            'prefix': self.get_form_prefix(step, form_class), 
            'initial': self.get_form_initial(step), 
        }) 
        if issubclass(form_class, (forms.ModelForm, forms.models.BaseInlineFormSet)): 
            # If the form is based on ModelForm or InlineFormSet, 
            # add instance if available and not previously set. 
            kwargs.setdefault('instance', self.get_form_instance(step)) 
        elif issubclass(form_class, forms.models.BaseModelFormSet): 
            # If the form is based on ModelFormSet, add queryset if available 
            # and not previous set. 
            kwargs.setdefault('queryset', self.get_form_instance(step)) 
        return form_class(**kwargs) 
         
    def merge(self): 
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
        original = self.model.objects.get(pk=original_pk) 
        from DBentry.utils import merge_records 
        merge_records(original, self.qs, update_data, expand) 
         
    def done(self, form_list, **kwargs): 
        self.merge() 
        try: 
            del self.request.session['merge'] 
        except Exception as e: 
            print('maint.views.MergeViewWizarded:380', e) 
        return redirect(self.success_url) 