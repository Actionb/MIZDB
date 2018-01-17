from collections import OrderedDict

from django import views
from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied

from .models import *
from .utils import link_list
from DBentry.forms import FavoritenForm
from .admin import miz_site

from dal import autocomplete
from formtools.wizard.views import SessionWizardView

class MIZAdminView(views.View):
    template_name = 'admin/basic.html'
    submit_value = 'Ok'
    submit_name = '_ok'
    
    @classmethod
    def has_permission(cls, request):
        # Default permission level: is_staff
        return request.user.is_staff
    
    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission(request):
            raise PermissionDenied
        return super(MIZAdminView, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, *args, **kwargs):
        if 'view' not in kwargs:
            kwargs['view'] = self
        # Add admin site context
        kwargs.update(miz_site.each_context(self.request))
        # Add custom context data for the submit button
        kwargs['submit_value'] = self.submit_value
        kwargs['submit_name'] = self.submit_name
        kwargs['is_popup'] = '_popup' in self.request.GET
        return kwargs
        
class FavoritenView(MIZAdminView, views.generic.UpdateView):
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

class MIZSessionWizardView(MIZAdminView, SessionWizardView):
    
    def get_context_data(self, form = None, *args, **kwargs):
        # SessionWizardView takes form as first positional argument, while MIZAdminView (and any other view) takes it as a kwarg.
        # Ensure form ends up in **kwargs for super
        form = form or kwargs.get('form', None)
        return super(MIZSessionWizardView, self).get_context_data(form=form, *args, **kwargs)
        
class DynamicChoiceFormMixin(object):
    
    def get_form_choices(self, form):
        pass
