from .base import *

from django.contrib.admin import helpers

from DBentry.admin import BandAdmin, AusgabenAdmin, ArtikelAdmin

from DBentry.actions.base import *
from DBentry.actions.views import *
from DBentry.forms import MIZAdminForm, forms
from DBentry.utils import get_obj_link # parameters: obj, user, admin_site

class TestActionConfirmationView(ActionViewTestCase, LoggingTestMixin):
    
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
        expected = [[get_obj_link(self.obj1, request.user)]]
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
       
class TestBulkEditJahrgang(ActionViewTestCase, LoggingTestMixin):
    
    view_class = BulkEditJahrgang
    model = ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [    
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001]}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001]}, 
        {'magazin__magazin_name':'Bad', 'jahrgang' : 20, 'ausgabe_jahr__jahr': [2001]}, 
        {'magazin__magazin_name':'Testmagazin'}
    ]
    
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
        
    def test_compile_affected_objects(self):
        # result 0 0 => obj1
        # result 0 1 => obj1.affected_fields
        # result 1 0 => obj3
        # result 1 1 => obj3.affected_fields
        # affected_fields for this view: ['jahrgang','ausgabe_jahr__jahr']
        request = self.get_request()
        
        view = self.view(request, queryset=self.qs_obj1)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        
        view = self.view(request, queryset=self.qs_obj3)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: 20", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        
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
    
    def test_post_show_confirmation_page(self):
        # get an ACTUAL response
        request = self.post_request()
        view = self.view(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        from django.template.response import TemplateResponse
        self.assertEqual(response.__class__, TemplateResponse)
    
    def test_dispatch_action_not_allowed(self):
        # Two different magazines
        request = self.post_request()
        view = self.view(request, queryset=self.model.objects.filter(pk__in=[self.obj2.pk, self.obj3.pk]))
        response = view.dispatch(request)
        self.assertIsNone(response)
        
    @tag('logging')
    def test_perform_action(self): 
        request = self.get_request()
        view = self.view(request)
        view.perform_action({'jahrgang':31416})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416, 31417])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')
        
    @tag('logging')
    def test_perform_action_no_years(self):    
        # obj4 has no years assigned, perform_action should assign it the value given by the 'form'
        request = self.get_request()
        view = self.view(request, queryset=self.qs_obj4)
        view.perform_action({'jahrgang':31416})
        new_jg = list(self.qs_obj4.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416])
        self.assertLoggedChange(self.obj4, 'jahrgang')
        
    @tag('logging')
    def test_perform_action_jahrgang_zero(self):   
        request = self.get_request()   
        view = self.view(request)
        view.perform_action({'jahrgang':0})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [None, None])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')
   
class TestBulkAddBestand(ActionViewTestCase, LoggingTestMixin):
    
    view_class = BulkAddBestand
    model = ausgabe
    model_admin_class = AusgabenAdmin
    
    @classmethod
    def setUpTestData(cls):
        cls.bestand_lagerort = make(lagerort, pk=ZRAUM_ID, ort='Bestand')
        cls.dubletten_lagerort = make(lagerort, pk=DUPLETTEN_ID, ort='Dublette')
        mag = make(magazin, magazin_name = 'Testmagazin')
        
        cls.obj1 = make(ausgabe, magazin=mag)
        cls.obj2 = make(ausgabe, magazin=mag, bestand__lagerort=cls.bestand_lagerort)
        cls.obj3 = make(ausgabe, magazin=mag, bestand__lagerort=cls.dubletten_lagerort)
        cls.obj4 = make(ausgabe, magazin=mag, bestand__lagerort=[cls.bestand_lagerort, cls.dubletten_lagerort])
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        super().setUpTestData()
    
    def test_compile_affected_objects_obj1(self):
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj1)
        obj_link = get_obj_link(self.obj1, request.user)
        related_links = []
        expected = [[obj_link, related_links]]
        self.assertEqual(view.compile_affected_objects(), expected)
    
    def test_compile_affected_objects_obj2(self):
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj2)
        obj_link = get_obj_link(self.obj2, request.user)
        related_links = [
            get_obj_link(obj, request.user)
            for obj in self.obj2.bestand_set.all()
        ]
        expected = [[obj_link, related_links]]
        self.assertEqual(view.compile_affected_objects(), expected)
    
    def test_compile_affected_objects_obj3(self):
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj3)
        obj_link = get_obj_link(self.obj3, request.user)
        related_links = [
            get_obj_link(obj, request.user)
            for obj in self.obj3.bestand_set.all()
        ]
        expected = [[obj_link, related_links]]
        self.assertEqual(view.compile_affected_objects(), expected)
        
    def test_compile_affected_objects_obj4(self):
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj4)
        obj_link = get_obj_link(self.obj4, request.user)
        related_links = [
            get_obj_link(obj, request.user)
            for obj in self.obj4.bestand_set.all()
        ]
        expected = [[obj_link, related_links]]
        self.assertEqual(view.compile_affected_objects(), expected)
       
    @tag('logging')      
    def test_perform_action_obj1(self):
        # obj1 has no bestand at all; this should add a 'bestand' bestand (hurrr) 
        old_bestand = list(self.obj1.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj1)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        all_bestand = list(self.obj1.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj1.bestand_set.exclude(pk__in=old_bestand)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj1, new_bestand.first())
        
    @tag('logging') 
    def test_perform_action_obj2(self):
        # obj2 has one 'bestand' bestand; this should add a dublette
        old_bestand = list(self.obj2.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj2)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        all_bestand = list(self.obj2.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        
        new_bestand = self.obj2.bestand_set.exclude(pk__in=old_bestand)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj2, new_bestand.first())
        
    @tag('logging') 
    def test_perform_action_obj3(self):
        # obj3 has one dubletten bestand; this should add a bestand 
        old_bestand = list(self.obj3.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj3)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        all_bestand = list(self.obj3.bestand_set.values_list('lagerort', flat=True))
        expected = [self.dubletten_lagerort.pk, self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        
        new_bestand = self.obj3.bestand_set.exclude(pk__in=old_bestand)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj3, new_bestand.first())
        
    @tag('logging') 
    def test_perform_action_obj4(self):
        # obj4 has both bestand and dubletten bestand; this should add a dublette
        old_bestand = list(self.obj4.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.view(request=request, queryset=self.qs_obj4)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        new_bestand = list(self.obj4.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(new_bestand, expected)
        
        new_bestand = self.obj4.bestand_set.exclude(pk__in=old_bestand)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj4, new_bestand.first())
        
    @tag('logging') 
    def test_perform_action(self):
        # Record the bestand of the objects before the action
        old_bestand1 = list(self.obj1.bestand_set.values_list('pk', flat=True))
        old_bestand2 = list(self.obj2.bestand_set.values_list('pk', flat=True))
        old_bestand3 = list(self.obj3.bestand_set.values_list('pk', flat=True))
        old_bestand4 = list(self.obj4.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.view(request=request)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        # obj1
        all_bestand = list(self.obj1.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj1.bestand_set.exclude(pk__in=old_bestand1)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj1, new_bestand.first())
        
        # obj2
        all_bestand = list(self.obj2.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj2.bestand_set.exclude(pk__in=old_bestand2)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj2, new_bestand.first())
        
        # obj3
        all_bestand = list(self.obj3.bestand_set.values_list('lagerort', flat=True))
        expected = [self.dubletten_lagerort.pk, self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj3.bestand_set.exclude(pk__in=old_bestand3)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj3, new_bestand.first())
        
        # obj4
        all_bestand = list(self.obj4.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj4.bestand_set.exclude(pk__in=old_bestand4)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj4, new_bestand.first())
        
    def test_get_initial(self):
        view = self.view()
        initial = view.get_initial()
        
        self.assertTrue('bestand' in initial)
        self.assertEqual(initial.get('bestand'), self.bestand_lagerort)
        self.assertTrue('dublette' in initial)
        self.assertEqual(initial.get('dublette'), self.dubletten_lagerort)

class TestMergeViewWizardedAusgabe(ActionViewTestCase): 
    # Note that tests concerning logging for this view are done on test_utils.merge_records directly.
    
    view_class = MergeViewWizarded
    model = ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [    
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000]}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001], 'jahrgang':1}, 
        {'magazin__magazin_name':'Bad', 'ausgabe_jahr__jahr': [2001], 'jahrgang' : 20}, 
        {'magazin__magazin_name':'Testmagazin', 'jahrgang':2}
    ]
    
    def test_action_allowed(self):
        queryset = self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view = self.view(queryset=queryset)
        self.assertTrue(view.action_allowed())
    
    def test_action_allowed_low_qs_count(self):
        request = self.post_request()
        view = self.view(request=request, queryset=self.qs_obj1)
        self.assertFalse(view.action_allowed())
        expected_message = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.'
        self.assertMessageSent(request, expected_message)
        
    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed())
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        self.assertMessageSent(request, expected_message)
        
    def test_post_action_not_allowed(self):
        # If the action is not allowed, post should REDIRECT us back to the changelist
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj3.pk]}
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        self.assertMessageSent(response.wsgi_request, expected_message)
        
    def test_post_first_visit(self):
        # post should return the first form of the Wizard
        # Cannot *really* test this here: we need a response from the RequestFactory to check the context (to check the right form_class).
        # To get that we would need to call self.client.post(model_admin.changelist,{action:action_name}), which would route through
        # ModelAdmin.changelist first, then ModelAdmin.response_action, then DBentry.actions.actions, and THEN DBentry.actions.views.MergeViewWizarded.post()
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk]}
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'admin/action_confirmation_wizard.html')
        self.assertIsInstance(response.context_data.get('form'), MergeFormSelectPrimary)
        self.assertIsInstance(response.context.get('wizard').get('form'), MergeFormSelectPrimary)
        
    def test_post_first_form_invalid(self):
        # post should not continue
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk]}
        management_form = {'current_step':0}
        request_data.update(management_form)
        form_data = {'original':None}
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data.get('form'), MergeFormSelectPrimary)
        self.assertIsInstance(response.context.get('wizard').get('form'), MergeFormSelectPrimary)
        
    def test_post_merge_conflict(self):
        # post should return the form that handles merge conflicts
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk, self.obj4.pk]}
        management_form = {'merge_view_wizarded-current_step':0}
        request_data.update(management_form)
        form_data = {'0-original':self.obj1.pk, '0-expand_o':True}
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data.get('form'), MergeConflictsFormSet)
        self.assertIsInstance(response.context.get('wizard').get('form'), MergeConflictsFormSet)
        
    def test_post_merge_conflict_success(self):
        # merge_conflicts have been resolved, post should REDIRECT (through response_action) us back to the changelist
        
        # Step 0
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk, self.obj4.pk]}
        management_form = {'merge_view_wizarded-current_step':0}
        request_data.update(management_form)
        form_data = {'0-original':self.obj1.pk, '0-expand_o':True}
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        
        # Step 1
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk, self.obj4.pk]}
        management_form = {
            'merge_view_wizarded-current_step':1, 
            '1-INITIAL_FORMS':'0', 
            '1-MAX_NUM_FORMS':'', 
            '1-MIN_NUM_FORMS':'', 
            '1-TOTAL_FORMS':'1',                 
        }
        request_data.update(management_form)
        form_data = {
            '1-0-verbose_fld_name':'Jahrgang', 
            '1-0-original_fld_name':'jahrgang', 
            '1-0-posvals':0, 
        }
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        
    def test_post_first_form_valid_and_no_merge_conflict(self):
        # post should return us back to the changelist
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk]}
        management_form = {'merge_view_wizarded-current_step':0}
        request_data.update(management_form)
        form_data = {'0-original':self.obj1.pk, '0-expand_o':True}
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        
    def test_merge_not_updating_fields_it_should_not(self):
        # Check that the whole process does *NOT* change already present data of the selected primary/original object 
        # spice up obj1 so we can verify that a merge has happened
        self.qs_obj1.update(beschreibung='I really should not be here.')
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk, self.obj4.pk]}
        management_form = {'merge_view_wizarded-current_step':0}
        request_data.update(management_form)
        # select obj2 (or obj4) here as original as it already has a value for jahrgang (our only 'source' of conflict)
        form_data = {'0-original':self.obj2.pk, '0-expand_o':True}
        request_data.update(form_data)
        
        response = self.client.post(self.changelist_path, data=request_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        
        self.obj2.refresh_from_db()
        self.assertEqual(self.obj2.jahrgang, 1)
        self.assertEqual(self.obj2.beschreibung, 'I really should not be here.')
      

class TestMergeViewWizardedArtikel(ActionViewTestCase): 
    
    view_class = MergeViewWizarded
    model = artikel
    model_admin_class = ArtikelAdmin
    test_data_count = 2
        
    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed())
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(request, expected_message)
