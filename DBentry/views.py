from collections import OrderedDict

from django import views
from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.contrib import admin, messages
from django.contrib.auth.mixins import UserPassesTestMixin

from .models import *
from .utils import link_list
from DBentry.forms import FavoritenForm
from .admin import miz_site

from dal import autocomplete
from formtools.wizard.views import SessionWizardView

class MIZAdminMixin(object):
    """
    A mixin that provides an admin 'look and feel' to custom views by adding admin_site specific context (each_context).
    """
    admin_site = miz_site
    
    def get_context_data(self, *args, **kwargs):
        kwargs = super(MIZAdminMixin, self).get_context_data(*args, **kwargs)
        # Add admin site context
        kwargs.update(self.admin_site.each_context(self.request))
        # Enable popups behaviour for custom views
        kwargs['is_popup'] = '_popup' in self.request.GET
        return kwargs
        
class MIZAdminPermissionMixin(MIZAdminMixin, UserPassesTestMixin):
    """
    A mixin that enables permission restricted views.
    """
    
    def permission_test(self):
        """
        The test function that the user has to pass for contrib.auth's UserPassesTestMixin to access the view.
        Default permission level is: is_staff
        """
        return self.request.user.is_staff
    
    def test_func(self):
        """
        Redirect the test for UserPassesTestMixin to a more aptly named function.
        """
        return self.permission_test()
        
class MIZAdminToolView(MIZAdminPermissionMixin, views.generic.TemplateView):
    """
    The base view for all 'Admin Tools'. 
    """
    
    template_name = 'admin/basic.html'
    submit_value = 'Ok'
    submit_name = '_ok'
    
    @staticmethod
    def show_on_index_page(request):
        """
        If the current user does not have required permissions, the view link will not be displayed on the index page.
        """
        # Default permission level: is_staff
        return request.user.is_staff
    
    def get_context_data(self, *args, **kwargs):
        kwargs = super(MIZAdminViewMixin, self).get_context_data(*args, **kwargs)
        # Add custom context data for the submit button
        kwargs['submit_value'] = self.submit_value
        kwargs['submit_name'] = self.submit_name
        return kwargs
        
class FavoritenView(MIZAdminToolView, views.generic.UpdateView):
    form_class = FavoritenForm
    template_name = 'admin/favorites.html'
    model = Favoriten
    
    url_name = 'favoriten'
    index_label = 'Favoriten Verwaltung'
        
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

miz_site.register_tool(FavoritenView)

class MIZSessionWizardView(MIZAdminPermissionMixin, SessionWizardView):
    
    def get_context_data(self, form = None, *args, **kwargs):
        # SessionWizardView takes form as first positional argument, while MIZAdminView (and any other view) takes it as a kwarg.
        # Ensure form ends up in **kwargs for super
        form = form or kwargs.get('form', None)
        return super(MIZSessionWizardView, self).get_context_data(form=form, *args, **kwargs)
        
class DynamicChoiceFormMixin(object):
    
    def get_form_choices(self, form):
        pass
