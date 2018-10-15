from django.http import Http404
from django.views.generic import TemplateView 
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.text import capfirst

from DBentry.sites import register_tool
from DBentry.views import MIZAdminMixin, MIZAdminToolViewMixin
from DBentry.utils import has_admin_permission

@register_tool
class HelpIndexView(MIZAdminToolViewMixin, TemplateView):
    """
    The view displaying an index over all available helptexts.
    Attributes:
        - registry: the registry of helptexts available to this view instance 
            set during initialization by the url resolver (see help.registry.get_urls)
    """

    # register_tool vars
    url_name = 'help_index' # Used in the admin_site.index
    index_label = 'Hilfe' # label for the tools section on the index page

    template_name = 'admin/help_index.html' 
    site_title = breadcrumbs_title = 'Hilfe'
    
    registry = None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if context.get('is_popup', False):
            html_template = '<a href="{url}?_popup=1">{label}</a>'
        else:
            html_template = '<a href="{url}">{label}</a>'
            
        # ModelAdmin Helptexts
        registered_models = []
        for model_admin in self.registry.get_registered_models():
            model_help, url_name = self.registry._registry[model_admin]
            if not has_admin_permission(self.request, model_admin):
                continue
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue
            registered_models.append((
                url, 
                model_help.index_title or capfirst(model_admin.opts.verbose_name_plural)
            ))
            
        # Sort by model_help.index_title // model._meta.verbose_name_plural
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
        for formview_class in self.registry.get_registered_forms():
            form_help, url_name = self.registry._registry[formview_class]
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                continue
            if not FormHelpView.has_permission(self.request): #TODO: need a better place for the permission check
                continue
                
            registered_forms.append((
                url, 
                form_help.index_title or 'Hilfe für ' + str(form_help.form_class)
            ))
            
        form_helps = []
        # Sort by form_help.index_title // str(form_help.form_class)
        for url, label in sorted(registered_forms, key = lambda tpl: tpl[1]):
            form_helps.append(format_html(
                html_template, 
                url = url, 
                label = label, 
            ))
        context['form_helps'] = form_helps
        
        return context

class BaseHelpView(MIZAdminMixin, TemplateView):
    """
    The base class for the HelpViews
    Attributes:
        - template_name: inherited from TemplateView
        - helptext_class: the helptext class this view is going to serve
        - registry: the registry of helptexts available to this view instance 
            set during initialization by the url resolver (see help.registry.get_urls)
    """
     
    template_name = 'admin/help.html' 
    helptext_class = None
    
    registry = None
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404 as e:
            # Return to the index page on encountering Http404.
            messages.warning(request, e.args[0])
            return redirect('help_index')
            
    def get_help_text(self, **kwargs):
        """
        Returns the HelpText instance (not wrapped) for this view.
        """
        if self.helptext_class is None:
            raise Exception("You must set a helptext class.")
        if 'registry' not in kwargs:
            kwargs['registry'] = self.registry
        return self.helptext_class(**kwargs)
        
class FormHelpView(BaseHelpView):
    """
    The view for displaying help texts for a particular form.
    
    Attributes:
        - target_view_class: the view that contains the form
    """
    
    target_view_class = None

    @classmethod
    def has_permission(cls, request):
        """
        Checks if the request has the required permissions to access this view.
        Returns True by default unless the target view is subclassing MIZAdminPermissionMixin,
        in which case the target view's permission_test classmethod is called.
        This is used in the index view to determine whether or not to show a link to this view on the index.
        """
        from DBentry.views import MIZAdminPermissionMixin
        if cls.target_view_class and issubclass(cls.target_view_class, MIZAdminPermissionMixin):
            return cls.target_view_class.permission_test(request)
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # for_context() wraps the helptext into a helper object that includes
        # the methods html() and sidenav(), which are expected by the template
        context.update(self.get_help_text(request = self.request).for_context())
        return context
        
class ModelAdminHelpView(BaseHelpView):
    """
    The view for displaying help texts for a model admin.
    The model admin is provided as initkwarg by the url resolver.
    
    Attributes:
        - model_admin: set by help.registry.HelpRegistry.get_urls
    """
    
    template_name = 'admin/help.html'
    
    model_admin = None
        
    def has_permission(self, request):
        if self.model_admin:
            # calls utils.has_admin_permission
            return has_admin_permission(request, self.model_admin)
        return False
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # for_context() wraps the helptext into a helper object that includes
        # the methods html() and sidenav(), which are expected by the template
        context.update(self.get_help_text(request = self.request, model_admin = self.model_admin).for_context())
        if not context.get('breadcrumbs_title', ''):
            context['breadcrumbs_title'] = self.model_admin.opts.verbose_name_plural
        if not context.get('site_title', ''):
            context['site_title'] = self.model_admin.opts.verbose_name_plural + ' Hilfe'
        return context
    
