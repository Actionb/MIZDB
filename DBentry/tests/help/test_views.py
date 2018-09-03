from copy import deepcopy

from ..base import *

from DBentry.help.helptext import ModelHelpText
from DBentry.help.registry import halp
from DBentry.help.views import *

class RegistryRestoreMixin(object):
    
    def setUp(self):
        super().setUp()
        self.registry_backup = deepcopy(halp._registry) # _registry is a nested dict
        
    def tearDown(self):
        super().tearDown()
        halp._registry = self.registry_backup
    
        
class TestHelpIndexView(RegistryRestoreMixin, ViewTestCase):
    
    path = '/admin/help/'
    view_class = HelpIndexView
        
    def test_get_context_data_models(self):
        view = self.get_view(request = self.get_request(user = self.noperms_user))
        context = view.get_context_data()
        self.assertIn('model_helps', context)
        self.assertEqual(context['model_helps'], [], msg = "User without any model permissions should not have access to any model helps.")
        
        halp._registry = { 'models' : {
            artikel: type('ArtikelHelpText', (ModelHelpText, ), {'model':artikel}), 
            buch: type('BuchHelpText', (ModelHelpText, ), {'model':buch, 'help_title':'Beep'}),  
        }}
        
        view = self.get_view(request = self.get_request())
        context = view.get_context_data()
        self.assertIn('model_helps', context)
        model_helps = context['model_helps']
        self.assertEqual(len(model_helps), 2)
        
        html_template = '<a href="{url}{popup}">{label}</a>' 
        expected = html_template.format(url = '/admin/help/artikel/', popup = '', label = 'Artikel')
        self.assertEqual(model_helps[0], expected)
        expected = html_template.format(url = '/admin/help/buch/', popup = '', label = 'Beep')
        self.assertEqual(model_helps[1], expected)
        
        # As a popup
        view = self.get_view(request = self.get_request(path = self.path + '?_popup=1'))
        context = view.get_context_data()
        self.assertIn('model_helps', context)
        model_helps = context['model_helps']
        self.assertEqual(len(model_helps), 2)
        
        html_template = '<a href="{url}{popup}">{label}</a>' 
        expected = html_template.format(url = '/admin/help/artikel/', popup = '?_popup=1', label = 'Artikel')
        self.assertEqual(model_helps[0], expected)
        expected = html_template.format(url = '/admin/help/buch/', popup = '?_popup=1', label = 'Beep')
        self.assertEqual(model_helps[1], expected)
    
class TestBaseHelpView(RegistryRestoreMixin, ViewTestCase):
    
    view_class = ModelHelpView
    
    def test_dispatch_redirects_to_index_on_404(self):
        response = self.client.get(reverse('help', kwargs = {'model_name':'arglblargl'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('help_index'), msg = "Should redirect to the help index on unknown models.")
        self.assertMessageSent(response.wsgi_request, "Das Modell mit Namen 'arglblargl' existiert nicht.")
        
        response = self.client.get(reverse('help', kwargs = {'model_name':'sender'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('help_index'), msg = "Should redirect to the help index on missing help page.")
        self.assertMessageSent(response.wsgi_request, "Hilfe für Modell Sender nicht gefunden.")
        
        halp._registry['models'][ausgabe_jahr] = None
        response = self.client.get(reverse('help', kwargs = {'model_name':'ausgabe_jahr'}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('help_index'), msg = "Should redirect to the help index on missing admin model.")
        self.assertMessageSent(response.wsgi_request, "Keine Admin Seite for Modell Jahr gefunden.")


class TestModelHelpView(RegistryRestoreMixin, ViewTestCase):
    
    path = '/admin/help/artikel'
    view_class = ModelHelpView
    
    def test_get_help_text(self):
        request = self.get_request()
        view = self.get_view(request = request, kwargs = {'model_name':'sender'})
        with self.assertRaises(Http404):
            view.get_help_text(request)
            
        request = self.get_request()
        view = self.get_view(request = request, kwargs = {'model_name':'artikel'})
        with self.assertNotRaises(Http404):
            help_object = view.get_help_text(request)
            self.assertIsInstance(help_object, ModelHelpText)
        
    def test_model_property(self):
        request = self.get_request()
        view = self.get_view(request = request, kwargs = {'model_name':'arglblargl'})
        with self.assertRaises(Http404):
            view.model
        
        view = self.get_view(request = request, kwargs = {'model_name':'artikel'})
        self.assertEqual(view.model, artikel)
        
    def test_model_admin_property(self):
        request = self.get_request()
        view = self.get_view(request = request, kwargs = {'model_name':'ausgabe_jahr'}) # has no AdminModel
        with self.assertRaises(Http404):
            view.model_admin
        
        view = self.get_view(request = request, kwargs = {'model_name':'artikel'})
        self.assertIsInstance(view.model_admin, ArtikelAdmin)
        
    def test_get_context_data(self):
        view = self.get_view(request = self.get_request(), kwargs = {'model_name':'artikel'})
        context = view.get_context_data()
        self.assertEqual(context.get('breadcrumbs_title', ''), artikel._meta.verbose_name, msg = "Breadcrumbs Title should default to the verbose name of the model.")
        self.assertEqual(context.get('site_title', ''), artikel._meta.verbose_name + ' Hilfe', msg = "Site Title should default to verbose_name of the model + ' Hilfe'")
        
