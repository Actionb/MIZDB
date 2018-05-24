from collections import OrderedDict

from django import views
from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.contrib import admin, messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import get_permission_codename
from django.utils.functional import cached_property

from .models import *
from .utils import link_list, model_from_string
from .forms import FavoritenForm
from .sites import miz_site, register_tool
from .constants import PERM_DENIED_MSG

from dal import autocomplete
from formtools.wizard.views import SessionWizardView

class OptionalFormView(views.generic.FormView):
    
    def get_form(self, form_class=None):
        if self.get_form_class() is None:
            # Form has become optional
            return None
        return super(OptionalFormView, self).get_form(form_class)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form is None or form.is_valid():
            # form is not given (because it's optional) OR form is given and is valid
            return self.form_valid(form)
        else:
            # back to FormView's form_invalid(): return self.render_to_response(self.get_context_data(form=form))
            return self.form_invalid(form)

class MIZAdminMixin(object):
    """
    A mixin that provides an admin 'look and feel' to custom views by adding admin_site specific context (each_context).
    """
    title = None
    breadcrumbs_title = None
    admin_site = miz_site
    
    def get_context_data(self, *args, **kwargs):
        context = super(MIZAdminMixin, self).get_context_data(*args, **kwargs)
        # Add admin site context
        context.update(self.admin_site.each_context(self.request))
        # Enable popups behaviour for custom views
        context['is_popup'] = '_popup' in self.request.GET
        if self.title: context['title'] = self.title
        if self.breadcrumbs_title: context['breadcrumbs_title'] = self.breadcrumbs_title
        return context
        
class MIZAdminPermissionMixin(MIZAdminMixin, UserPassesTestMixin):
    """
    A mixin that enables permission restricted views.
    """
    permission_denied_message = PERM_DENIED_MSG
    raise_exception = True
    _permissions_required = []
    
    #@cached_property
    @classmethod
    def get_permissions_required(cls):
        permissions_required = []
        for perm_tuple in cls._permissions_required:
            model = None
            if isinstance(perm_tuple, str):
                perm_code = perm_tuple
            elif len(perm_tuple)==1:
                perm_code = perm_tuple[0]
            else:
                perm_code, model = perm_tuple
                if isinstance(model, str):
                    model = model_from_string(model)
            if model is None:
                if hasattr(cls, 'opts'):
                    opts = getattr(cls, 'opts')
                elif hasattr(cls, 'model'):
                    opts = getattr(cls, 'model')._meta
                else:
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured("No model/opts set for permission code '{}'. ".format(perm_code)+\
                        "To explicitly set required permissions, create a list of permission codenames as an attribute named 'permissions_required'."
                        )
            else:
                opts = model._meta
            perm = '{}.{}'.format(opts.app_label, get_permission_codename(perm_code, opts))
            permissions_required.append(perm)
        return permissions_required
    
    @classmethod
    def permission_test(cls, request):
        """
        The test function that the user has to pass for contrib.auth's UserPassesTestMixin to access the view.
        Default permission level is: is_staff
        """
        permissions_required = cls.get_permissions_required()
        if permissions_required:
            for perm in permissions_required:
                if not request.user.has_perm(perm):
                    return False
            return True
        else:
            return request.user.is_staff
        
    def test_func(self):
        """
        Redirect the test for UserPassesTestMixin to a more aptly named function.
        """
        return self.permission_test(self.request)
        
class MIZAdminToolViewMixin(MIZAdminPermissionMixin):
    """
    The base mixin for all 'Admin Tools'. 
    """
    
    submit_value = None
    submit_name = None
    form_method = 'post'
    template_name = 'admin/basic.html'
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.submit_value: context['submit_value'] = self.submit_value
        if self.submit_name: context['submit_name']  = self.submit_name
        context['form_method'] = self.form_method
        return context
            
    
    @staticmethod
    def show_on_index_page(request):
        """
        Returns whether or not link to this view should be displayed on the index page.
        This will be overriden by permission_test() of MIZAdminPermissionMixin, if specific permissions are required.
        """
        return request.user.is_staff

@register_tool
class FavoritenView(MIZAdminToolViewMixin, views.generic.UpdateView):
    form_class = FavoritenForm
    template_name = 'admin/favorites.html'
    model = Favoriten
    
    url_name = 'favoriten'
    index_label = 'Favoriten Verwaltung'
    
    _permissions_required = [('add', 'Favoriten'), ('change', 'Favoriten'), ('delete', 'Favoriten')]
        
    def get_success_url(self):
        # Redirect back onto this site
        return ''
    
    def get_object(self):
        # user field on Favoriten is unique, so at most a single user can have one set of favorites or none
        object = Favoriten.objects.filter(user=self.request.user).first()
        if object is None:
            # user has no favorites yet, create an entry in Favoriten model
            object = Favoriten(user=self.request.user)
            object.save()
        return object        
        
        
class FixedSessionWizardView(SessionWizardView):
    
    def get_context_data(self, form = None, *args, **kwargs):
        # SessionWizardView takes form as first positional argument, while MIZAdminView (and any other view) takes it as an (optional) kwarg.
        # Ensure form ends up in **kwargs for super
        form = form or kwargs.get('form', None)
        return super(FixedSessionWizardView, self).get_context_data(form=form, *args, **kwargs)
         
    def get_form(self, step=None, data=None, files=None): 
        """ Here the bit of WizardView.get_form that causes problems:
            kwargs = self.get_form_kwargs(step)
            kwargs.update({
                'data': data,
                'files': files,
                'prefix': self.get_form_prefix(step, form_class),
                'initial': self.get_form_initial(step),
            })
            If data=None/{} and we prepare kwargs['data'] (for example) in get_form_kwargs, the following update on kwargs overwrites anything we have done.
        """ 
        if step is None: 
            step = self.steps.current 
        kwargs = self.get_form_kwargs(step)
        data = data or kwargs.get('data', None)
        files = files or kwargs.get('files', None)
        return super(FixedSessionWizardView, self).get_form(step, data, files) 
        
class DynamicChoiceFormMixin(object):
    
    def get_form_choices(self, form):
        pass
    
# views for the django default handlers
def MIZ_permission_denied_view(request, exception, template_name='admin/403.html'):
    from django.template import TemplateDoesNotExist, loader
    from django import http
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return http.HttpResponseForbidden('<h1>403 Forbidden</h1>', content_type='text/html')
    
    from django.template.response import TemplateResponse
    context = {'exception' : str(exception) if str(exception) else PERM_DENIED_MSG}
    context.update(miz_site.each_context(request))
    context['is_popup'] = '_popup' in request.GET 
    return TemplateResponse(request, template_name, context=context)
