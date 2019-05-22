from unittest.mock import patch, Mock

from .base import ActionViewTestCase
from ..base import AdminTestCase, mockv, mockex
from ..mixins import LoggingTestMixin

from django.test import tag
from django.contrib.admin import helpers
from django.utils.translation import override as translation_override
from django.db.models.deletion import ProtectedError

import DBentry.models as _models
from DBentry.factory import make
from DBentry.admin import BandAdmin, AusgabenAdmin, ArtikelAdmin, AudioAdmin
from DBentry.actions.base import ActionConfirmationView, ConfirmationViewMixin, WizardConfirmationView
from DBentry.actions.views import BulkEditJahrgang, BulkAddBestand, MergeViewWizarded, MoveToBrochureBase
from DBentry.actions.forms import MergeConflictsFormSet, MergeFormSelectPrimary
from DBentry.forms import MIZAdminForm, forms
from DBentry.utils import get_obj_link # parameters: obj, user, admin_site
from DBentry.views import MIZAdminMixin, FixedSessionWizardView
from DBentry.sites import miz_site
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID

from formtools.wizard.views import SessionWizardView, WizardView

class TestConfirmationViewMixin(AdminTestCase):
    
    model = _models.audio
    model_admin_class = AudioAdmin
    
    def get_instance(self, **kwargs):
        initkwargs = dict(model_admin = self.model_admin, queryset = self.model.objects.all())
        initkwargs.update(kwargs)
        return ConfirmationViewMixin(**initkwargs)
    
    def test_init_sets_action_name(self):
        ConfirmationViewMixin.action_name = 'test'
        instance = self.get_instance()
        self.assertEqual(instance.action_name, 'test')
        
        # init should set action_name if the class does not have that attribute
        ConfirmationViewMixin.action_name = None
        instance = self.get_instance()
        self.assertTrue(hasattr(instance, 'action_name'))
        self.assertEqual(instance.action_name, instance.__class__.__name__)
        
    def test_perform_action_not_implemented(self):
        # this base class has not implemented the perform_action method
        instance = self.get_instance()
        with self.assertRaises(NotImplementedError):
            instance.perform_action()
    
    def test_dispatch_action_not_allowed(self):
        # dispatch should redirect 'back' (here: return None) if the action is not allowed
        instance = self.get_instance()
        instance.action_allowed = mockv(False)
        self.assertIsNone(instance.dispatch(self.get_request()))
    
    @translation_override(language = None)
    @patch.object(MIZAdminMixin, 'get_context_data', return_value = {})
    def test_get_context_data(self, m):
        instance = self.get_instance()
        instance.title = 'Mergeaudio'
        instance.breadcrumbs_title = 'Breads'
        
        context = instance.get_context_data()
        self.assertEqual(context.get('title'), 'Mergeaudio')
        self.assertEqual(context.get('breadcrumbs_title'), 'Breads')
        self.assertEqual(context.get('non_reversible_warning'), instance.non_reversible_warning)
        self.assertEqual(context.get('objects_name'), instance.opts.verbose_name_plural)
        
        instance.title = ''
        instance.short_description = 'Testdescription'
        instance.breadcrumbs_title = ''
        instance.action_reversible = True
        instance.queryset = [1]
        context = instance.get_context_data()
        self.assertEqual(context.get('title'), 'Testdescription')
        self.assertEqual(context.get('breadcrumbs_title'), 'Testdescription')
        self.assertEqual(context.get('non_reversible_warning'), '')
        self.assertEqual(context.get('objects_name'), instance.opts.verbose_name)

class TestActionConfirmationView(ActionViewTestCase):
    
    view_class = ActionConfirmationView
    model = _models.band
    model_admin_class = BandAdmin
    test_data_count = 1
    
    def test_get_form_class(self):
        # get_form_class should create a 'selection form' form class if the view has no form_class assigned
        # view fields not set => super().get_form_class() ====> None
        view = self.get_view()
        self.assertEqual(view.get_form_class(), None)
        
        # view.fields set and no view.form_class set 
        # => makeSelectionForm should make a form (here: a MIZAdminForm)
        view.selection_form_fields = ['band_name']
        with patch('DBentry.actions.base.makeSelectionForm', return_value = 'SelectionForm'):
            self.assertEqual(view.get_form_class(), 'SelectionForm')
        form_class = view.get_form_class()
        self.assertTrue(issubclass(form_class, MIZAdminForm))
        self.assertEqual(form_class.__name__, 'SelectionForm')
        
        view.form_class = forms.Form
        self.assertEqual(view.get_form_class(), forms.Form)
    
    def test_compile_affected_objects(self):
        request = self.get_request()
        view = self.get_view(request=request)
        expected = [[get_obj_link(self.obj1, request.user)]]
        self.assertEqual(view.compile_affected_objects(), expected)
        
        a = make(_models.audio, sender = make(_models.sender), band = self.obj1,format__extra = 2)
        view = self.get_view(request, model_admin = AudioAdmin(_models.audio, miz_site), queryset = _models.audio.objects.all())
        view.affected_fields = ['titel', 'sender', 'band__band_name', 'format___name', 'release_id']
        link_list = view.compile_affected_objects() # [ ['Audio Material: <link>', [<affected objects>]], ]
        self.assertEqual(link_list[0][0], get_obj_link(a, request.user))
        self.assertEqual(link_list[0][1][0], 'Titel: '+ a.titel)
        self.assertEqual(link_list[0][1][1], get_obj_link(a.sender, request.user))
        self.assertEqual(link_list[0][1][2], get_obj_link(a.band.first(), request.user))
        self.assertEqual(link_list[0][1][3], get_obj_link(a.format_set.all()[0], request.user))
        self.assertEqual(link_list[0][1][4], get_obj_link(a.format_set.all()[1], request.user))
        self.assertEqual(link_list[0][1][5], 'Release ID (discogs): ---')
        
    def test_form_valid(self):
        # form_valid should redirect back to the changelist 
        # a return value of None will make options.ModelAdmin.response_action redirect there
        view = self.get_view()
        view.perform_action = Mock()
        self.assertIsNone(view.form_valid(None))
    
    @tag("wip")
    def test_context_contains_additional_confirmations(self):
        view = self.get_view(self.get_request())
        context = view.get_context_data()
        self.assertIn('additional_confirmations', context)
        
class TestWizardConfirmationView(ActionViewTestCase):
    
    view_class = WizardConfirmationView
    model = _models.audio
    model_admin_class = AudioAdmin
    
    @patch.object(ConfirmationViewMixin, 'get_context_data', return_value = {})
    def test_get_context_data(self, m):
        # get_context_data should add helptext for the current step
        view = self.get_view()
        view.steps = Mock(current = '1')
        context = view.get_context_data()
        self.assertNotIn('view_helptext', context)
        
        view.view_helptext = {
            '1': 'Step 1', 
            '2': 'Step 2'
        }
        context = view.get_context_data()
        self.assertIn('view_helptext', context)
        self.assertEqual(context['view_helptext'], 'Step 1')
        view.steps = Mock(current = '2')
        context = view.get_context_data()
        self.assertIn('view_helptext', context)
        self.assertEqual(context['view_helptext'], 'Step 2')
    
    @patch.object(SessionWizardView, 'post', return_value = 'WizardForm!')
    @patch.object(FixedSessionWizardView, '__init__')
    def test_post(self, x, y):
        # If there is no 'step' data in request.POST, post() should return the rendered first form of the wizard.
        request = self.post_request()
        view = self.get_view(request)
        view.storage = Mock()
        view.steps = Mock(first = '1')
        view.get_form = mockv('The first form!')
        view.render = mockv('Rendered form.')
        self.assertEqual(view.post(request), 'Rendered form.')
        self.assertEqual(view.storage.reset.call_count, 1)
        self.assertEqual(view.render.call_count, 1)
        view.storage.current_step = '1'
        
        prefix = 'wizard_confirmation_view' # SessionWizardView -> WizardView -> normalize_name
        request = self.post_request(data = {prefix + '-current_step':'2'})
        self.assertEqual(view.post(request), 'WizardForm!')

class TestBulkEditJahrgang(ActionViewTestCase, LoggingTestMixin):
    
    view_class = BulkEditJahrgang
    model = _models.ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [    
        { # obj1: jg + 0
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 
            'e_datum': '2000-06-12', 'ausgabe_monat__monat__ordinal': [6]
        },
        { # obj2: jg + 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001], 
            'e_datum': '2001-06-12', 'ausgabe_monat__monat__ordinal': [6]
        },
        { # obj3: ignored
            'magazin__magazin_name':'Bad', 'jahrgang' : 20, 'ausgabe_jahr__jahr': [2001]
        },
        { # obj4: ignored?
            'magazin__magazin_name':'Testmagazin'
        }, 
        {  # obj5: jg + 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2002], 
            'e_datum': '2002-05-11', 'ausgabe_monat__monat__ordinal': [5], 
        },
        {  # obj6: jg + 2 when using e_datum, jg + 1 when using monat
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2002], 
            'e_datum': '2002-06-12', 'ausgabe_monat__monat__ordinal': [5]
        },
        {  # obj7: jg + 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001]
        },
        {  # obj8: jg + 2
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2002]
        },
    ]
    
    def setUp(self):
        super(TestBulkEditJahrgang, self).setUp()
        self.queryset = self.model.objects.exclude(pk=self.obj3.pk)
        
    def test_action_allowed(self):
        self.assertTrue(self.get_view().action_allowed())
        
        request = self.get_request()
        view = self.get_view(request, queryset=self.model.objects.filter(ausgabe_jahr__jahr=2001))
        view.model_admin.message_user = Mock()
        self.assertFalse(view.action_allowed())
        
        expected_message = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin." 
        view.model_admin.message_user.assert_called_once_with(request, expected_message, 'error')
    
    def test_compile_affected_objects(self):
        # result 0 0 => obj1
        # result 0 1 => obj1.affected_fields
        # result 1 0 => obj2
        # result 1 1 => obj2.affected_fields
        # affected_fields for this view: ['jahrgang','ausgabe_jahr__jahr']
        request = self.get_request()
        
        view = self.get_view(request, queryset=self.qs_obj1)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        
        view = self.get_view(request, queryset = self.queryset)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        expected = ["Jahrgang: ---", "Jahr: 2001"]
        self.assertEqual(result[1][1], expected)
        
        view = self.get_view(request, queryset=self.qs_obj3)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: 20", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        
    def test_post_action_not_allowed(self):
        # If the action is not allowed, post should REDIRECT us back to the changelist
        request_data = {'action':'bulk_jg', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj3.pk]}
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        expected_message = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
        self.assertMessageSent(response.wsgi_request, expected_message)
        
    def test_post_show_confirmation_page(self):
        # get an ACTUAL response
        request = self.post_request()
        view = self.get_view(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        from django.template.response import TemplateResponse
        self.assertEqual(response.__class__, TemplateResponse)
        
    @tag('logging')
    def test_perform_action(self): 
        request = self.get_request()
        view = self.get_view(request)
        view.perform_action({'jahrgang':31416, 'start':self.obj1.pk})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True).exclude(jahrgang=None).distinct())
        self.assertEqual(new_jg, [31416, 31417, 31418])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')
        
    @tag('logging')
    def test_perform_action_no_years(self):    
        # obj4 has no years assigned, perform_action should assign it the jahrgang value given by 'form_cleaned_data'
        request = self.get_request()
        view = self.get_view(request, queryset=self.qs_obj4)
        form_cleaned_data = {'jahrgang':31416, 'start':self.obj4.pk}
        view.perform_action(form_cleaned_data)
        new_jg = list(self.qs_obj4.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416])
        self.assertLoggedChange(self.obj4, 'jahrgang')
        
    @tag('logging')
    def test_perform_action_jahrgang_zero(self):   
        request = self.get_request()   
        view = self.get_view(request)
        view.perform_action({'jahrgang':0, 'start':self.obj1.pk})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True).distinct())
        self.assertEqual(new_jg, [None])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')
            
class TestBulkAddBestand(ActionViewTestCase, LoggingTestMixin):
    
    view_class = BulkAddBestand
    model = _models.ausgabe
    model_admin_class = AusgabenAdmin
    
    @classmethod
    def setUpTestData(cls):
        cls.bestand_lagerort = make(_models.lagerort, pk=ZRAUM_ID, ort='Bestand')
        cls.dubletten_lagerort = make(_models.lagerort, pk=DUPLETTEN_ID, ort='Dublette')
        mag = make(_models.magazin, magazin_name = 'Testmagazin')
        
        cls.obj1 = make(cls.model, magazin=mag)
        cls.obj2 = make(cls.model, magazin=mag, bestand__lagerort=cls.bestand_lagerort)
        cls.obj3 = make(cls.model, magazin=mag, bestand__lagerort=cls.dubletten_lagerort)
        cls.obj4 = make(cls.model, magazin=mag, bestand__lagerort=[cls.bestand_lagerort, cls.dubletten_lagerort])
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        super().setUpTestData()
        
    def test_compile_affected_objects(self):
        link_template = 'Bestand: <a href="/admin/DBentry/bestand/{pk}/change/">{lagerort__ort}</a>'
        
        request = self.get_request()
        view = self.get_view(request)
        link_list = view.compile_affected_objects()
        self.assertEqual(len(link_list), 4)
        # obj1
        self.assertFalse(link_list[0][1])
        # obj2
        self.assertIn(link_template.format(**self.obj2.bestand_set.values('pk', 'lagerort__ort')[0]), link_list[1][1])
        # obj3 
        self.assertIn(link_template.format(**self.obj3.bestand_set.values('pk', 'lagerort__ort')[0]), link_list[2][1])
        # obj4 
        self.assertIn(link_template.format(**self.obj4.bestand_set.values('pk', 'lagerort__ort')[0]), link_list[3][1])
        self.assertIn(link_template.format(**self.obj4.bestand_set.values('pk', 'lagerort__ort')[1]), link_list[3][1])
   
    @tag('logging') 
    def test_perform_action(self):
        # Record the bestand of the objects before the action
        old_bestand1 = list(self.obj1.bestand_set.values_list('pk', flat=True))
        old_bestand2 = list(self.obj2.bestand_set.values_list('pk', flat=True))
        old_bestand3 = list(self.obj3.bestand_set.values_list('pk', flat=True))
        old_bestand4 = list(self.obj4.bestand_set.values_list('pk', flat=True))
        
        request = self.get_request()
        view = self.get_view(request=request)
        view.perform_action({'bestand':self.bestand_lagerort, 'dublette':self.dubletten_lagerort})
        
        # obj1 has no bestand at all; this should add a 'bestand' bestand (hurrr)
        all_bestand = list(self.obj1.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj1.bestand_set.exclude(pk__in=old_bestand1)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj1, new_bestand.first())
        
        # obj2 has one 'bestand' bestand; this should add a dublette
        all_bestand = list(self.obj2.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj2.bestand_set.exclude(pk__in=old_bestand2)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj2, new_bestand.first())
        
        # obj3 has one dubletten bestand; this should add a bestand 
        all_bestand = list(self.obj3.bestand_set.values_list('lagerort', flat=True))
        expected = [self.dubletten_lagerort.pk, self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj3.bestand_set.exclude(pk__in=old_bestand3)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj3, new_bestand.first())
        
        # obj4 has both bestand and dubletten bestand; this should add a dublette
        all_bestand = list(self.obj4.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj4.bestand_set.exclude(pk__in=old_bestand4)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj4, new_bestand.first())
        
    def test_get_initial(self):
        view = self.get_view()
        initial = view.get_initial()
        
        self.assertTrue('bestand' in initial)
        self.assertEqual(initial.get('bestand'), self.bestand_lagerort)
        self.assertTrue('dublette' in initial)
        self.assertEqual(initial.get('dublette'), self.dubletten_lagerort)

class TestMergeViewWizardedAusgabe(ActionViewTestCase): 
    # Note that tests concerning logging for this view are done on test_utils.merge_records directly.
    #TODO: there is no unit test for MergeViewWizarded.perform_action
    view_class = MergeViewWizarded
    model = _models.ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [    
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000]}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001], 'jahrgang':1}, 
        {'magazin__magazin_name':'Bad', 'ausgabe_jahr__jahr': [2001], 'jahrgang' : 20}, 
        {'magazin__magazin_name':'Testmagazin', 'jahrgang':2}
    ]
    
    def test_action_allowed(self):
        queryset = self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view = self.get_view(queryset=queryset)
        self.assertTrue(view.action_allowed())
    
    def test_action_allowed_low_qs_count(self):
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.qs_obj1)
        self.assertFalse(view.action_allowed())
        expected_message = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.'
        self.assertMessageSent(request, expected_message)
        
    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
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
        # post should return the first form (form_class: MergeFormSelectPrimary) of the Wizard
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk]}
        
        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'admin/action_confirmation_wizard.html')
        self.assertIsInstance(response.context_data.get('form'), MergeFormSelectPrimary)
        self.assertIsInstance(response.context.get('wizard').get('form'), MergeFormSelectPrimary)
        
    def test_post_first_form_invalid(self):
        # post should not continue
        #NOTE: the first form actually cannot fail??
        request_data = {'action':'merge_records', helpers.ACTION_CHECKBOX_NAME : [self.obj1.pk, self.obj2.pk]}
        management_form = {'current_step':0}
        request_data.update(management_form)
        form_data = {'original':''}
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
    
    @patch('DBentry.actions.views.get_updateable_fields', return_value = [])
    @patch.object(SessionWizardView, 'process_step', return_value = {})
    def test_process_step(self, super_process_step, updateable_fields):
        view = self.get_view()
        view.get_form_prefix = mockv('0')
        view.storage = Mock(current_step = '')
        view.steps = Mock(last='No conflicts->Last step')
        form = MergeFormSelectPrimary()
        
        # if expand_o is False in MergeFormSelectPrimary, there cannot be any conflicts
        # and the last step should be up next
        form.cleaned_data = {'expand_o':False}
        self.assertEqual(view.process_step(form), {})
        self.assertEqual(view.storage.current_step, 'No conflicts->Last step')
        
        # if the 'original' has no fields that can be updated, the returned dict should not contain 'updates'
        super_process_step.return_value = {'0-original':self.obj1.pk}
        form.cleaned_data = {'0-original':self.obj1.pk, 'expand_o':True}
        self.assertEqual(view.process_step(form), {'0-original':self.obj1.pk})
                
        # obj1 can be updated on the field 'jahrgang' with obj2's value
        updateable_fields.return_value = ['jahrgang']
        view.queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view.storage.current_step = ''
        processed_data = view.process_step(form)
        self.assertIn('updates', processed_data)
        self.assertIn('jahrgang', processed_data['updates'])
        self.assertEqual(processed_data['updates']['jahrgang'], ['1'])
        self.assertEqual(view.storage.current_step, 'No conflicts->Last step')
        
        # same as above, but with a conflict due to involving obj4 as well
        view.queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk])
        view.storage.current_step = ''
        processed_data = view.process_step(form)
        self.assertIn('updates', processed_data)
        self.assertIn('jahrgang', processed_data['updates'])
        self.assertListEqualSorted(processed_data['updates']['jahrgang'], ['1', '2'])
        self.assertEqual(view.storage.current_step, '')
    
    @translation_override(language = None)
    @patch.object(WizardConfirmationView, 'get_context_data', return_value = {})
    def test_get_context_data(self, super_get_context_data):
        # Assert that 'title' is counting up with 'step'
        view = self.get_view()
        view.steps = Mock(current = '0')
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 1')
        view.steps.current = '22'
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 23')
    
    @patch.object(WizardView, 'get_form_kwargs', return_value = {})
    def test_get_form_kwargs(self, super_get_form_kwargs):
        view = self.get_view(queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk]))
        # MergeFormSelectPrimary step
        form_kwargs = view.get_form_kwargs(step = '0')
        self.assertIn('choices', form_kwargs)
        self.assertListEqualSorted(
            view.queryset.values_list('pk', flat = True), form_kwargs['choices'].values_list('pk', flat = True)
        )
        
        # MergeConflictsFormSet step
        view.form_list = {'1':MergeConflictsFormSet}
        view._updates = {'jahrgang':['1', '2'], 'beschreibung':['Test']}
        form_kwargs = view.get_form_kwargs(step = '1')
        self.assertIn('data', form_kwargs)
        expected = {
            '1-TOTAL_FORMS': 1, '1-MAX_NUM_FORMS': '', '1-0-original_fld_name': 'jahrgang', 
            '1-INITIAL_FORMS': '0', '1-0-verbose_fld_name': 'Jahrgang'
        }
        self.assertEqual(form_kwargs['data'], expected)
        self.assertIn('form_kwargs', form_kwargs)
        self.assertIn('choices', form_kwargs['form_kwargs'])
        self.assertEqual(form_kwargs['form_kwargs']['choices'], {'1-0-posvals': [(0, '1'), (1, '2')]})
    
    @translation_override(language = None)
    @patch.object(MergeViewWizarded, 'perform_action', new = mockex(ProtectedError('msg', _models.artikel.objects.all())))
    def test_done(self):
        # Assert that an admin message is send to user upon encountering a ProtectedError during done
        request = self.get_request()
        view = self.get_view(request = request)
        view.done()
        self.assertMessageSent(request, 'Folgende verwandte Artikel verhinderten die Zusammenführung:')
        

class TestMergeViewWizardedArtikel(ActionViewTestCase): 
    
    view_class = MergeViewWizarded
    model = _models.artikel
    model_admin_class = ArtikelAdmin
    test_data_count = 2
        
    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed())
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(request, expected_message)
        
class TestMoveToBrochureBase(ActionViewTestCase):
    
    view_class = MoveToBrochureBase
    model = _models.ausgabe
    model_admin_class = AusgabenAdmin
    
    raw_data = [
        {
            'beschreibung': 'Testausgabe', 'sonderausgabe': True, 
            'bestand__extra': 1, 'ausgabe_jahr__jahr': [2000, 2001], 
            'magazin__magazin_name': 'Testmagazin'
        }
    ]
    
    def setUp(self):
        super().setUp()
        self.form_cleaned_data = [
            {
                'brochure_art': 'Brochure', 'titel': 'Testausgabe', 'ausgabe_id': self.obj1.pk, 'accept': True, 
            }
        ]
    
    @translation_override(language = None)
    def test_action_allowed_has_artikels(self):
        self.obj1.artikel_set.add(make(_models.artikel))
        request = self.post_request()
        view = self.get_view(request = request, queryset = self.queryset)
        self.assertFalse(view.action_allowed())
        expected_message = "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht verschoben werden können: "
        expected_message += '<a href="/admin/DBentry/ausgabe/{}/change/">Testausgabe</a>'.format(str(self.obj1.pk))
        self.assertMessageSent(request, expected_message)
        
    def test_action_allowed(self):
        view = self.get_view(request = self.post_request(), queryset = self.queryset)
        self.assertTrue(view.action_allowed())
        
    def test_get_initial(self):
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        initial = view.get_initial()
        self.assertEqual(len(initial), 1)
        self.assertIn('ausgabe_id', initial[0])
        self.assertEqual(initial[0]['ausgabe_id'], self.obj1.pk)
        self.assertIn('titel', initial[0])
        self.assertEqual(initial[0]['titel'], self.obj1.magazin.magazin_name)
        self.assertIn('zusammenfassung', initial[0])
        self.assertEqual(initial[0]['zusammenfassung'], self.obj1.beschreibung)
        self.assertIn('bemerkungen', initial[0])
        self.assertEqual(initial[0]['bemerkungen'], self.obj1.bemerkungen)
    
    def test_perform_action(self):
        self.form_cleaned_data[0]['zusammenfassung'] = 'Bleep bloop' # should make it into the new record
        self.form_cleaned_data[0]['beschreibung'] = '' # empty value, should NOT make it into the new record
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
       
        changed_bestand = self.obj1.bestand_set.first()
        self.assertEqual(_models.Brochure.objects.count(), 0)
        view.perform_action(self.form_cleaned_data)
        self.assertEqual(_models.Brochure.objects.count(), 1)
        new_brochure = _models.Brochure.objects.get()
        
        # Inspect the brochure attributes
        self.assertEqual(new_brochure.titel, 'Testausgabe')
        self.assertEqual(new_brochure.zusammenfassung, 'Bleep bloop')
        self.assertFalse(new_brochure.beschreibung)
        # Inspect the bestand
        changed_bestand.refresh_from_db()
        self.assertEqual(new_brochure.bestand_set.first(), changed_bestand)
        self.assertIsNone(changed_bestand.ausgabe_id)
        # Assert that the original was deleted
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())
        
    def test_perform_action_moves_jahre(self):
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        view.perform_action(self.form_cleaned_data)
        new_brochure = _models.Brochure.objects.get()
        self.assertEqual(list(new_brochure.jahre.values_list('jahr', flat = True)), [2000, 2001])
        
    def test_perform_action_adds_hint_to_bemerkungen(self):
        expected = "Hinweis: {verbose_name} wurde automatisch erstellt beim Verschieben von Ausgabe {str_ausgabe} (Magazin: {str_magazin})."
        expected = expected.format(
            verbose_name = _models.Brochure._meta.verbose_name, 
            str_ausgabe = str(self.obj1), str_magazin = str(self.obj1.magazin)
        )
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        view.perform_action(self.form_cleaned_data)
        new_brochure = _models.Brochure.objects.get()
        self.assertIn(expected, new_brochure.bemerkungen)
    
    def test_perform_action_skips_invalid_brochure_classes(self):
        self.form_cleaned_data[0]['brochure_art'] = ''
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        
        view.perform_action(self.form_cleaned_data)
        # Assert that the ausgabe was not deleted
        self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
        self.assertEqual(_models.BaseBrochure.objects.count(), 0)
     
    def test_perform_action_katalog(self):
        self.form_cleaned_data[0]['brochure_art'] = 'Katalog'
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        
        self.assertEqual(_models.Katalog.objects.count(), 0)
        view.perform_action(self.form_cleaned_data)
        self.assertEqual(_models.Katalog.objects.count(), 1)
     
    def test_perform_action_kalendar(self):
        self.form_cleaned_data[0]['brochure_art'] = 'Kalendar'
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        
        self.assertEqual(_models.Kalendar.objects.count(), 0)
        view.perform_action(self.form_cleaned_data)
        self.assertEqual(_models.Kalendar.objects.count(), 1)
     
    @patch('DBentry.actions.views.get_model_from_string')   
    def test_perform_action_protected_ausgabe(self, mocked_model_from_string):
        mocked_model_from_string.return_value = _models.Brochure
        
        self.obj1.artikel_set.add(make(_models.artikel, ausgabe_id = self.obj1.pk))
        request = self.get_request()
        view = self.get_view(request = request, queryset = self.queryset)
        
        view.perform_action(self.form_cleaned_data)
        self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
        expected_message = "Folgende Ausgaben konnten nicht gelöscht werden: " + \
            '<a href="/admin/DBentry/ausgabe/{pk}/change/">{name}</a>'.format(pk = self.obj1.pk, name = str(self.obj1)) + \
            ". Es wurden keine Broschüren für diese Ausgaben erstellt."
        self.assertMessageSent(request, expected_message)
        
        # No new brochure objects should have been created
        self.assertEqual(_models.Brochure.objects.count(), 0)
    
    @patch('DBentry.actions.views.get_model_from_string')
    @translation_override(language = None)
    def test_perform_action_protected_magazin(self, mocked_model_from_string):
        def is_protected(instances):
            # The check for protection should pass for ausgaben but not for the magazin
            if isinstance(instances[0], self.model):
                return False
            return True
        mocked_model_from_string.return_value = _models.Brochure
        
        mag = self.obj1.magazin 
        self.form_cleaned_data[0]['delete_magazin'] = True
        request = self.get_request()
        view = self.get_view(request = request, queryset = self.queryset)
        
        with patch('DBentry.actions.views.is_protected', new = is_protected):
            view.perform_action(self.form_cleaned_data)
        self.assertTrue(_models.magazin.objects.filter(pk=mag.pk).exists())
        expected_message = "Folgende Magazine konnten nicht gelöscht werden: " + \
            '<a href="/admin/DBentry/magazin/{pk}/change/">{name}</a>'.format(pk = mag.pk, name = str(mag))
        self.assertMessageSent(request, expected_message)
    
    @patch('DBentry.actions.views.is_protected')  
    @patch('DBentry.actions.views.get_model_from_string')
    def test_perform_action_does_not_roll_back_ausgabe_deletion(self, mocked_model_from_string, mocked_is_protected):
        # Assert that a rollback on trying to delete the magazin does not also roll back the ausgabe
        mocked_model_from_string.return_value = _models.Brochure
        mocked_is_protected.return_value = False
        
        ausgabe_id = self.obj1.pk
        magazin_id = self.obj1.magazin_id
        make(self.model, magazin_id = magazin_id) # Create an ausgabe that will force a ProtectedError
        self.form_cleaned_data[0]['delete_ausgabe'] = self.form_cleaned_data[0]['delete_magazin'] = True
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        
        view.perform_action(self.form_cleaned_data)
        self.assertFalse(self.model.objects.filter(pk=ausgabe_id).exists())
        self.assertTrue(_models.magazin.objects.filter(pk=magazin_id).exists())
        
    def test_perform_action_not_accepted(self):
        ausgabe_id = self.obj1.pk
        self.form_cleaned_data[0]['accept'] = False
        view = self.get_view(request = self.get_request(), queryset = self.queryset)
        
        view.perform_action(self.form_cleaned_data)
        self.assertTrue(self.model.objects.filter(pk=ausgabe_id).exists())
        self.assertEqual(_models.BaseBrochure.objects.count(), 0)
    
    def test_init_does_not_disable_delete_magazin_when_working_on_entire_ausgaben_set(self):
        # Assert that a form's delete_magazin field is not disabled if the action is being performed on
        # the full set of ausgaben of this magazin - and thus would allow deleting the magazin in the end.
        new_obj = make(self.model, magazin=self.obj1.magazin)
        request = self.get_request()
        view = self.get_view(request = request, queryset = self.model.objects.filter(pk__in=[self.obj1.pk, new_obj.pk]))
        if any(form.fields['delete_magazin'].disabled for form in view.get_form()):
            self.fail('delete_magazin field disabled.')
        
    def test_magazin_protection_status_updates(self):
        # Assert that magazines are not longer present in the protected_mags list when all of 
        # their ausgaben were affected by this action.
        new_obj = make(self.model, magazin=self.obj1.magazin)
        request = self.get_request()
        view = self.get_view(request = request, queryset = self.model.objects.filter(pk__in=[self.obj1.pk, new_obj.pk]))
        form_cleaned_data = [
            { 'brochure_art': 'Brochure', 'titel': 'Testausgabe', 'ausgabe_id': self.obj1.pk, 'accept': True, 'delete_magazin': True}, 
            { 'brochure_art': 'Brochure', 'titel': 'Testausgabe', 'ausgabe_id': new_obj.pk, 'accept': True, 'delete_magazin': True}
        ]
        view.perform_action(form_cleaned_data)
        self.assertFalse(_models.magazin.objects.filter(pk=self.obj1.magazin.pk).exists())
        self.assertMessageNotSent(request, "Folgende Magazine konnten nicht gelöscht werden:")
        
    def test_form_disables_delete_magazin_for_protected_magazines(self):
        make(self.model, magazin=self.obj1.magazin) # Protect ya magazin
        request = self.get_request()
        view = self.get_view(request = request, queryset = self.model.objects.filter(pk=self.obj1.pk))
        self.assertTrue(view.get_form()[0].fields['delete_magazin'].disabled)
    
    @tag("wip")
    def test_context_contains_additional_confirmations(self):
        view = self.get_view(self.get_request())
        context = view.get_context_data()
        self.assertIn('additional_confirmations', context)
        
        expected = (
            'Magazin löschen', 'delete_magazin', 
            'Soll das Magazin dieser Ausgabe anschließend gelöscht werden?'
        )
        self.assertIn(expected, context['additional_confirmations'])
        
    
