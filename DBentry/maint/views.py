
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
from DBentry.utils import get_obj_link, get_model_from_string, get_model_fields, get_model_relations, ensure_jquery

#TODO: fix this import
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
    #NOTE: check for 'get_duplicates' (name of submit button) in request.GET before doing a query for duplicates? 
    
    url_name = 'dupes_select' 
    index_label = 'Duplikate finden' 
    template_name = 'admin/dupes.html'
    form_class = DuplicateFieldsSelectForm
    _dupe_fields = None
    
    def dispatch(self, request, *args, **kwargs):
        self.model = get_model_from_string(kwargs.get('model_name'))
        self.opts = self.model._meta
        self.title = 'Duplikate: ' + self.opts.verbose_name 
        self.breadcrumbs_title = self.opts.verbose_name 
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        from DBentry.sites import miz_site
        response = None
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        if selected:
            # Items to be merged are selected, call the MergeViewWizarded view.
            queryset = self.model.objects.filter(pk__in=selected)
            model_admin = miz_site.get_admin_model(self.model)
            response = MergeViewWizarded.as_view(model_admin=model_admin, queryset=queryset)(request)
        if response:
            # MergeViewWizarded has returned a response (the merge conflict page)
            return response
        else:
            # MergeViewWizarded returned None (successful merge)
            # or there was nothing selected: redirect back here.
            return redirect(request.get_full_path())
        
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
               
        context['form'] = self.get_form()
        
        media = context.get('media', False)
        if media:
            media += context['form'].media
        else:
            media = context['form'].media
        context['media'] = ensure_jquery(media)
        
        context['headers'], context['items'] = self.build_duplicate_items_context(context['form'], self.dupe_fields)
        context['action_name'] = 'merge_records'
        context['action_checkbox_name'] = ACTION_CHECKBOX_NAME
        return context
        
    @property
    def dupe_fields(self):
        if self._dupe_fields is None:
            self._dupe_fields = []
            for formfield in self.form_class.base_fields: 
                if formfield in self.request.GET:
                    self._dupe_fields.extend(self.request.GET.getlist(formfield))
        return self._dupe_fields
        
    def get_form(self, model = None, dupe_fields = None):
        if dupe_fields is None:
            dupe_fields = self.dupe_fields
        return duplicatefieldsform_factory(model or self.model, dupe_fields)
        
    def build_duplicate_items_context(self, form = None, dupe_fields = None):
        """
        Returns a list of headers and a list of 2-tuples of:
            - a list of duplicate items (instance, link to change view, duplicate values)
            - a link to the changelist of these items
        """
        if dupe_fields is None:
            dupe_fields = self.dupe_fields
        if not dupe_fields:
            return [], []
        if form is None:
            form = self.get_form(self.model, dupe_fields)
            
        items = []
        duplicates = self.model.objects.duplicates(*dupe_fields)
        
        # Use the verbose name labels established in the fields select form for the table's headers.
        choices = {}
        for choice_field in form.fields.values():
            if not getattr(choice_field, 'choices', False):
                # Not a choice field ... somehow!
                continue
            field_choices = choice_field.choices
            if isinstance(field_choices[0][1], (list, tuple)):
                # Grouped choices: [('group_name',[*choices])]; get the actual choices
                field_choices = field_choices[0][1]
            choices.update(dict(field_choices))
                
        headers = [choices[f] for f in dupe_fields]
        for instances, values in duplicates:
            dupe_item = [
                (instance, get_obj_link(instance, self.request.user, include_name = False), [values[f] for f in dupe_fields])
                for instance in instances
            ]           
            cl_url =  reverse('admin:{}_{}_changelist'.format(self.opts.app_label, self.opts.model_name))
            cl_url += '?id__in={}'.format(",".join([str(instance.pk) for instance in instances]))
            items.append((dupe_item, cl_url))
        return headers, items
        
class ModelSelectView(MaintView, views.generic.FormView):
    
    submit_value = 'Weiter'
    form_method = 'get'
    form_class = ModelSelectForm
    next_view = None
    
    def get(self, request, *args, **kwargs):
        if request.GET.get('model_select'):
            return redirect(reverse(self.next_view, kwargs = {'model_name':request.GET.get('model_select')}))
        return super().get(request, *args, **kwargs)
    
    
