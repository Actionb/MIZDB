from django.http import Http404
from django.views.generic import TemplateView 
from django.urls import resolve, reverse
from django.urls.exceptions import NoReverseMatch
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.html import format_html

from DBentry.sites import register_tool
from DBentry.views import MIZAdminMixin, MIZAdminToolViewMixin
from DBentry.utils import get_model_from_string, get_model_admin_for_model, has_admin_permission

from DBentry.bulk.views import BulkAusgabe

from .registry import halp
from .models import *
from .forms import BulkFormHelpText

@register_tool
class HelpIndexView(MIZAdminToolViewMixin, TemplateView):

    # register_tool vars
    url_name = 'help_index' # Used in the admin_site.index
    index_label = 'Hilfe' # label for the tools section on the index page

    template_name = 'admin/help_index.html' 
    site_title = breadcrumbs_title = 'Hilfe'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if context.get('is_popup', False):
            html_template = '<a href="{url}?_popup=1">{label}</a>'
        else:
            html_template = '<a href="{url}">{label}</a>'
            
        # Model Helptexts
        registered_models = []
        for model, model_help in halp.get_registered_models().items():
            model_admin = getattr(model_help, 'model_admin', None) or get_model_admin_for_model(model)
            if not has_admin_permission(self.request, model_admin):
                continue
            try:
                url = reverse('help', kwargs = {'model_name': model._meta.model_name})
            except NoReverseMatch:
                continue
            registered_models.append((
                url, 
                model_help.help_title or model._meta.verbose_name_plural
            ))
        
        # Sort by model_help.help_title // model._meta.verbose_name_plural
        model_helps = []
        for url, label in sorted(registered_models, key = lambda tpl: tpl[1]):
            model_helps.append(format_html(
                html_template, 
                url = url, 
                label = label
            ))
        context['model_helps'] = model_helps
        
        # Form Helptexts
        registered_forms = []
        for url_name, form_help in halp.get_registered_forms().items():
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue
            resolver_match = resolve(url)
            if not resolver_match.func.view_class.has_permission(self.request):
                continue
                
            registered_forms.append((
                url, 
                form_help.help_title or 'Hilfe für ' + str(form_help.form_class)
            ))
            
        form_helps = []
        # Sort by form_help.help_title // str(form_help.form_class)
        for url, label in sorted(registered_forms, key = lambda tpl: tpl[1]):
            form_helps.append(format_html(
                html_template, 
                url = url, 
                label = label, 
            ))
        context['form_helps'] = form_helps
        
        return context

class BaseHelpView(MIZAdminMixin, TemplateView):
     
    template_name = 'admin/help.html' 
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404 as e:
            messages.warning(request, e.args[0])
            return redirect('help_index')
            
    def get_help_text(self, request = None):
        raise NotImplementedError()
        
class FormHelpView(BaseHelpView):
    
    form_helptext_class = None
    target_view_class = None
    
    def get_help_text(self, **kwargs):
        return self.form_helptext_class(**kwargs)
    
    @classmethod
    def has_permission(cls, request):
        from DBentry.views import MIZAdminPermissionMixin
        if cls.target_view_class and issubclass(cls.target_view_class, MIZAdminPermissionMixin):
            return cls.target_view_class.permission_test(request)
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_help_text(request = self.request).for_context())
        return context
        
class ModelHelpView(BaseHelpView):
    
    template_name = 'admin/help.html'
    
    _model = None
    _model_admin = None
    
    def get_help_text(self, request):
        if not halp.is_registered(self.model):
            raise Http404("Hilfe für Modell {} nicht gefunden.".format(self.model._meta.verbose_name))
        return halp.help_for_model(self.model)(request, self.model_admin)
    
    @property
    def model(self):
        if self._model is None:
            model_name = self.kwargs.get('model_name')
            self._model = get_model_from_string(model_name)
            if self._model is None:
                raise Http404("Das Modell mit Namen '{}' existiert nicht.".format(model_name))
        return self._model
        
    @property
    def model_admin(self):
        if self._model_admin is None:
            self._model_admin = get_model_admin_for_model(self.model)
            if self._model_admin is None:
                raise Http404("Keine Admin Seite for Modell {} gefunden.".format(self.model._meta.verbose_name))
        return self._model_admin
        
    def has_permission(self, request):
        if self.model_admin:
            return has_admin_permission(request, self.model_admin)
        return False
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_help_text(self.request).for_context())
        if self.model:
            context['breadcrumbs_title'] = self.model._meta.verbose_name
            context['site_title'] = self.model._meta.verbose_name + ' Hilfe'
        return context

class BulkFormAusgabeHelpView(FormHelpView):
    
    site_title = 'Hilfe für Ausgaben Erstellung'
    breadcrumbs_title = 'Ausgaben Erstellung'
    
    form_helptext_class = BulkFormHelpText
    target_view_class = BulkAusgabe
    
    
