from django import views
from django.shortcuts import render, redirect 
from django.http import HttpResponse 
 
from django.urls import reverse_lazy, reverse 
from django.db.models import Count 
from django.apps import apps 
 
from itertools import chain 
 
from DBentry.views import MIZAdminToolViewMixin 
from DBentry.models import * 
from DBentry.sites import register_tool
 
from .forms import * 

 
class MaintView(MIZAdminToolViewMixin, views.generic.TemplateView): 
    url_name = 'maint_main' 
    index_label = 'Wartung' 
    template_name = 'admin/basic.html' 
    success_url = reverse_lazy('admin:index') 
    
    @staticmethod 
    def show_on_index_page(request): 
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
