
from itertools import chain 

from django import views
from django.shortcuts import render, redirect 
from django.http import HttpResponse 
 
from django.urls import reverse_lazy, reverse 
from django.db.models import Count 
from django.apps import apps 
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.utils.http import urlencode
 
 
from DBentry.views import MIZAdminToolViewMixin, FixedSessionWizardView
from DBentry.actions.views import MergeViewWizarded
from DBentry.models import * 
from DBentry.sites import register_tool
from DBentry.utils import get_obj_link, get_model_from_string

from .forms import * 

#@register_tool
class MaintView(MIZAdminToolViewMixin, views.generic.TemplateView): 
    url_name = 'maint_main' 
    index_label = 'Wartung' 
    template_name = 'admin/basic.html' 
    success_url = reverse_lazy('admin:index') 
    title = 'Wartung'
    
    @staticmethod 
    def show_on_index_page(request): 
        # Only show a link on the index page if superuser
        return request.user.is_superuser 
        
    @classmethod
    def permission_test(cls, request):
        # Only allow superusers to access the page
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

@register_tool
class DuplicateObjectsView(MaintView):
    #TODO: provide more info for the select to merge bit
    
    url_name = 'dupes_select' 
    index_label = 'Duplikate finden' 
    template_name = 'admin/dupes.html'
    dupe_fields = None
    
    def dispatch(self, request, *args, **kwargs):
        self.model = get_model_from_string(kwargs.get('model_name'))
        self.opts = self.model._meta
        self.title = 'Duplikate: ' + self.opts.verbose_name 
        self.breadcrumbs_title = self.opts.verbose_name 
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        from DBentry.sites import miz_site
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        queryset = self.model.objects.filter(pk__in=selected)
        model_admin = miz_site.get_admin_model(self.model)
        response = MergeViewWizarded.as_view(model_admin=model_admin, queryset=queryset)(request)
        if response:
            return response
        else:
            return redirect(request.get_full_path())
                
    def get(self, request, *args, **kwargs):
        if 'fields' in request.GET:
            self.dupe_fields = request.GET.getlist('fields')
        return super().get(request, *args, **kwargs)
        
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        
        form_choices = [(f.name, f.verbose_name.capitalize()) for f in get_model_fields(self.model, foreign = True,  m2m = False)]
        form_initial = {'fields': self.dupe_fields} if self.dupe_fields else {}
        context['form'] = DuplicateFieldsSelectForm(choices=form_choices, initial = form_initial)
        
        media = context.get('media', False)
        if media:
            media += context['form'].media
        else:
            media = context['form'].media
        context['media'] = media
        
        items = []
        if self.dupe_fields:
            duplicates = self.model.objects.duplicates(*self.dupe_fields)
            
            context['headers'] = [self.opts.get_field(f).verbose_name for f in self.dupe_fields]
            for id_set, fields_dict in duplicates.items():
                dupe_item = []
                for id in id_set:
                    instance = self.model.objects.get(pk=id)
                    link = get_obj_link(instance, self.request.user, include_name=False)
                    dupe_item.append((instance, link, [fields_dict[f] for f in self.dupe_fields]))
                    
                cl_url =  reverse('admin:{}_{}_changelist'.format(self.opts.app_label, self.opts.model_name))
                cl_url += '?id__in={}'.format(",".join([str(id) for id in id_set]))
                items.append((dupe_item, cl_url))
            
        context['items'] = items
        context['action_name'] = 'merge_records'
        context['action_checkbox_name'] = ACTION_CHECKBOX_NAME
        return context
        
        
class ModelSelectView(MaintView, views.generic.FormView):
    
    submit_value = 'Weiter'
    form_method = 'get'
    form_class = ModelSelectForm
    next_view = None
    
    def get(self, request, *args, **kwargs):
        if request.GET.get('model_select'):
            return redirect(reverse(self.next_view, kwargs = {'model_name':request.GET.get('model_select')}))
        return super().get(request, *args, **kwargs)
    
    
