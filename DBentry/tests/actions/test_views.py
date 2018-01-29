from .base import *

from DBentry.admin import BandAdmin, AusgabenAdmin

from DBentry.actions.base import *
from DBentry.actions.views import *
from DBentry.forms import MIZAdminForm, forms

class TestActionConfirmationView(ActionViewTestCase):
    
    view_class = ActionConfirmationView
    model = band
    model_admin_class = BandAdmin
    test_data_count = 1
            
    def test_init_no_action_name(self):
        # Not setting an action_name attribute on view
        view = self.view()
        self.assertEqual(getattr(view, 'model_admin', None), self.model_admin)
        self.assertEqual(list(getattr(view, 'queryset', None)), list(self.queryset))
        self.assertEqual(getattr(view, 'action_name', None), view.__class__.__name__)
        self.assertEqual(getattr(view, 'opts', None), self.model_admin.opts)
        
    def test_init_with_action_name(self):
        # Setting an action_name attribute on view
        view = self.view(action_name='test_action')
        self.assertEqual(getattr(view, 'action_name', None), 'test_action')
        
    def test_get_form_class_fields_no_form_class(self):
        # 1. view.fields set and no view.form_class set => makeSelectionForm should make a form (so: a MIZAdminForm)
        view = self.view()
        view.fields = ['band_name']
        self.assertTrue(issubclass(view.get_form_class(), MIZAdminForm))
        
    def test_get_form_class_fields_and_form_class(self):
        # 2. view.fields set and view.form_class set => views.generic.FormView will take over with the provided form_class
        view = self.view()
        view.fields = ['band_name']
        view.form_class = forms.Form
        self.assertEqual(view.get_form_class(), forms.Form)
    
    def test_get_form_class_nada(self):
        # 3. view fields not set => super().get_form_class() ====> None
        view = self.view()
        self.assertEqual(view.get_form_class(), None)
        
    def test_perform_action_not_implemented(self):
        # this base class has not implemented the perform_action method
        view = self.view()
        with self.assertRaises(NotImplementedError):
            view.perform_action()
            
    def test_action_allowed(self):
        # defaults to True
        view = self.view()
        self.assertTrue(view.action_allowed())
    
    def test_compile_affected_objects(self):
        request = self.get_request()
        view = self.view(request=request)
        from DBentry.utils import get_obj_link #obj, opts, user, admin_site
        expected = [[get_obj_link(self.obj1, view.opts, request.user, view.model_admin.admin_site)]]
        self.assertEqual(view.compile_affected_objects(), expected)
        
    def test_get_context_data_one_item(self):
        request = self.get_request()
        view = self.view(request=request)
        context = view.get_context_data()
        self.assertEqual(context['objects_name'], self.model_admin.opts.verbose_name)
        
    def test_get_context_data_multiple_items(self):
        self.model.objects.create(band_name='Testband')
        queryset = self.model.objects.all()
        
        request = self.get_request()
        view = self.view(request=request, queryset=queryset)
        context = view.get_context_data()
        self.assertEqual(context['objects_name'], self.model_admin.opts.verbose_name_plural)
        
class TestBulkEditJahrgang(ActionViewTestCase):
    
    view_class = BulkEditJahrgang
    model = ausgabe
    model_admin_class = AusgabenAdmin
    
    @classmethod
    def setUpTestData(cls):
        mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.obj1 = ausgabe.objects.create(magazin=mag)
        cls.obj1.ausgabe_jahr_set.create(jahr=2000)
        
        cls.obj2 = ausgabe.objects.create(magazin=mag)
        cls.obj2.ausgabe_jahr_set.create(jahr=2001)
        
        cls.obj3 = ausgabe.objects.create(magazin=magazin.objects.create(magazin_name='Bad'))
        cls.obj3.ausgabe_jahr_set.create(jahr=2001)
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super(TestBulkEditJahrgang, cls).setUpTestData()
    
    def setUp(self):
        super(TestBulkEditJahrgang, self).setUp()
        # set self.queryset to objects 1 and 2 as these are compliant with the view's checks
        self.queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        
        
    def test_action_allowed(self):
        # the DataFactory assigns both ausgaben the same magazin
        self.assertTrue(self.view().action_allowed())
        
    def test_action_allowed_multi_magazine(self):
        request = self.get_request()
        view = self.view(request, queryset=self.model.objects.filter(ausgabe_jahr__jahr=2001))
        self.assertFalse(view.action_allowed())
        expected_message = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin." 
        self.assertMessageSent(request, expected_message)
        
    def test_form_valid(self):
        request = self.post_request(data={'action_confirmed':True, 'jahrgang':1})
        view = self.view(request)
        form = view.get_form()
        form.full_clean()
        self.assertIsNone(view.form_valid(form))
        
    def test_get_context_data_with_form(self):
        #TODO: how to compare media objects?
#        request = self.get_request()
#        view = self.view(request)
#        context = view.get_context_data()
#        media = context['media']
#        expected = self.model_admin.media + view.get_form().media
#        self.assertEqual(media, expected)
        pass
        
    # self.client.post(path=self.changelist_path,data={stuff})? --> nope this goes through ModelAdmin.response_action first   
    def test_post_action_confirmed(self):
        # If the posted form is valid, the post method (through form_valid()) should return None (redirecting us back to the changelist)
        request = self.post_request(data={'action_confirmed':True, 'jahrgang':1})
        view = self.view(request)
        response = view.post(request)
        self.assertIsNone(response)
        
    def test_post_action_aborted(self):
        request = self.post_request(data={'action_aborted':True})
        view = self.view(request)
        response = view.post(request)
        self.assertIsNone(response)
    
    def test_post_show_confirmation_page(self):
        # get an ACTUAL response
        request = self.post_request()
        view = self.view(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        from django.template.response import TemplateResponse
        self.assertEqual(response.__class__, TemplateResponse)
    
    def test_post_action_not_allowed(self):
        request = self.get_request()
        view = self.view(request, queryset=self.model.objects.filter(ausgabe_jahr__jahr=2001))
        response = view.post(request)
        self.assertIsNone(response)
        
    def test_perform_action(self):      
        view = self.view()
        view.perform_action({'jahrgang':31416})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416, 31417])
