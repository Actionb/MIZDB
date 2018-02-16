from django import forms
from .base import *

from DBentry.views import *
from DBentry.maint.views import *
from DBentry.ie.views import *
    
class TestOptionalFormView(ViewTestCase):
    
    view_class = OptionalFormView
    form_class = forms.Form
    
    def test_get_form(self):
        # OptionalFormView should return a form of the given form_class
        view = self.view(request=self.get_request(), form_class=self.form_class)
        self.assertIsInstance(view.get_form(), forms.Form)
        
    def test_get_form_no_formclass(self):
        # If no form_class is set (i.e. the form is optional), get_form() should return None
        view = self.view()
        self.assertIsNone(view.get_form())
        
        # Pass a dummy form_class to get_form(), it should still prioritize being optional
        self.assertIsNone(view.get_form(self.form_class))
        
    def test_post_form_is_none(self):
        # Test that the post method acknowledges the optional form
        request = self.post_request()
        view = self.view(request, success_url='Test')
        response = view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'Test')
        
class TestMIZAdminToolViewMixin(ViewTestCase):
    # includes tests for the mixins: MIZAdminMixin, MIZAdminPermissionMixin
    
    view_bases = (MIZAdminToolViewMixin, views.generic.TemplateView)
    
    def test_permission_test_only_staff_required(self):
        # basic test for user.is_staff as MIZAdminToolView does not set any required permissions
        view_class = self.get_dummy_view_class(attrs = {'model':band})
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(view_class.permission_test(request))
        self.assertFalse(view_class.show_on_index_page(request))
        
        request = self.get_request(user=self.staff_user)
        self.assertTrue(view_class.permission_test(request))
        self.assertTrue(view_class.show_on_index_page(request))
        
        request = self.get_request()
        self.assertTrue(view_class.permission_test(request))
        self.assertTrue(view_class.show_on_index_page(request))
        
    def test_permission_test_with_explicit_permreq(self):
        # setting MIZAdminToolView.permission_required 
        # none of the users actually have any permissions set other than is_staff/is_superuser
        view_class = self.get_dummy_view_class(attrs={'_permissions_required':['beepboop'], 'model':band})
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(view_class.permission_test(request))
        
        request = self.get_request(user=self.staff_user)
        self.assertFalse(view_class.permission_test(request))
        
        request = self.get_request()
        self.assertTrue(view_class.permission_test(request))
        
    def test_get_permissions_required(self):
        # See how get_permissions_required deals with various forms of setting model opts and permissions
        expected = ['DBentry.perm1_ausgabe', 'DBentry.perm2_ausgabe', 'DBentry.perm3_ausgabe', 'DBentry.perm4_ausgabe']
        attrs = {'_permissions_required': ['perm1', ('perm2', ), ('perm3', ausgabe), ('perm4', 'ausgabe')]} 
        
        # opts set on view
        _attrs = attrs.copy()
        _attrs.update(opts=ausgabe._meta)
        view_class = self.get_dummy_view_class(attrs=_attrs)
        self.assertEqual(view_class.get_permissions_required(), expected)        
        
        # model set on view
        _attrs = attrs.copy()
        _attrs.update(model=ausgabe)
        view_class = self.get_dummy_view_class(attrs=_attrs)
        self.assertEqual(view_class.get_permissions_required(), expected)      
        
        # no opts/model set on view => ImproperlyConfigured exception
        view_class = self.get_dummy_view_class(attrs=attrs)
        from django.core.exceptions import ImproperlyConfigured
        with self.assertRaises(ImproperlyConfigured):
            view_class.get_permissions_required()
        
    def test_get_context_data(self):
        request = self.get_request()
        context_data = self.get_dummy_view(request=request).get_context_data()
        self.assertEqual(context_data.get('is_popup', False), False)
        
        request = self.get_request(data={'_popup':1})
        context_data = self.get_dummy_view(request=request).get_context_data()
        self.assertEqual(context_data.get('is_popup', False), True)
    
class TestFavoritenView(ViewTestCase):
    
    view_class = FavoritenView
    path = reverse("favoriten")
    
    def test_get_success_url(self):
        request = self.get_request()
        view = self.view(request)
        self.assertEqual(view.get_success_url(), '')
    
    def test_get_object(self):
        # Test that get_object creates a new entry in the Favoriten table if necessary
        request = self.get_request()
        view = self.view(request)
        view.model.objects.filter(user=request.user).delete() # delete the entry that the test_view_available method created
        
        self.assertEqual(view.get_object().user, self.super_user) # user has no Favoriten yet, create an entry in Favoriten
        self.assertTrue(view.model.objects.filter(user=request.user).exists())
        self.assertEqual(view.get_object().user, self.super_user) # direct access to Favoriten via queryset

class TestPermissionDeniedView(TestCase):
    
    def test_MIZ_permission_denied_view_missing_template(self):
        response = MIZ_permission_denied_view(None, None, template_name='beepboop')
        from django import http
        self.assertTrue(isinstance(response, http.HttpResponseForbidden))
    
    def test_MIZ_permission_denied_view(self):
        from django.core.exceptions import PermissionDenied
        exception = PermissionDenied('Exception Text')
        request = self.client.get('').wsgi_request
        response = MIZ_permission_denied_view(request, exception)
        self.assertTrue('exception' in response.context_data)
        self.assertEqual(response.context_data['exception'], 'Exception Text')
        
        self.assertTrue('is_popup' in response.context_data)
