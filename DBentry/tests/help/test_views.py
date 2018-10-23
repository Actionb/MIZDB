from .base import *

from DBentry.help.helptext import ModelAdminHelpText
from DBentry.help.views import HelpIndexView, BaseHelpView, FormHelpView, ModelAdminHelpView

class TestHelpIndexView(HelpViewMixin, ViewTestCase):
    
    path = '/admin/help/'
    view_class = HelpIndexView
    
    def test_get_context_data_models(self):
        view = self.get_view(request = self.get_request(user = self.noperms_user), registry = self.registry)
        context = view.get_context_data()
        self.assertIn('model_helps', context)
        self.assertEqual(context['model_helps'], [], msg = "User without any model permissions should not have access to any model helps.")
        
        artikel_help = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
        buch_help = type('BuchHelpText', (ModelAdminHelpText, ), {'model':buch, 'index_title':'Beep'})
        self.registry.register(helptext = artikel_help, url_name = None)
        self.registry.register(helptext = buch_help, url_name = None)
        
        with add_urls(self.registry.get_urls(), '^admin/help/'):
            view = self.get_view(request = self.get_request(path=''), registry = self.registry)
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
            view = self.get_view(request = self.get_request(path = self.path + '?_popup=1'), registry = self.registry)
            context = view.get_context_data()
            self.assertIn('model_helps', context)
            model_helps = context['model_helps']
            self.assertEqual(len(model_helps), 2)
            
            html_template = '<a href="{url}{popup}">{label}</a>' 
            expected = html_template.format(url = '/admin/help/artikel/', popup = '?_popup=1', label = 'Artikel')
            self.assertEqual(model_helps[0], expected)
            expected = html_template.format(url = '/admin/help/buch/', popup = '?_popup=1', label = 'Beep')
            self.assertEqual(model_helps[1], expected)
    
class TestBaseHelpView(ViewTestCase):
    
    view_class = BaseHelpView
    
    def test_get_help_text(self):
        # Assert that get_help_text complains if no helptext_class is set
        view = self.get_view(helptext_class = None)
        with self.assertRaises(Exception):
            view.get_help_text()
            
class TestFormHelpView(ViewTestCase):
    
    view_class = FormHelpView 
    
    def test_permission_test(self):
        from DBentry.bulk.views import BulkAusgabe
        request = self.get_request(user = self.noperms_user)
        self.assertFalse(self.view_class.permission_test(request, BulkAusgabe))
        
        request = self.get_request(user = self.super_user)
        self.assertTrue(self.view_class.permission_test(request, BulkAusgabe))

class TestModelHelpView(ModelHelpViewTestCase):
    
    path = '/admin/help/artikel/'
    view_class = ModelAdminHelpView
    
    model = artikel
    model_admin_class = ArtikelAdmin
    
    helptext_class = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
    
    def test_permission_test(self):
        request = self.get_request(user = self.noperms_user)
        self.assertFalse(self.view_class.permission_test(request, self.model_admin))
        
        request = self.get_request(user = self.super_user)
        self.assertTrue(self.view_class.permission_test(request, self.model_admin))
        
    def test_get_context_data(self):
        view = self.get_view(request = self.get_request())
        context = view.get_context_data()
        self.assertEqual(context.get('breadcrumbs_title', ''), artikel._meta.verbose_name, msg = "Breadcrumbs Title should default to the verbose name of the model.")
        self.assertEqual(context.get('site_title', ''), artikel._meta.verbose_name + ' Hilfe', msg = "Site Title should default to verbose_name of the model + ' Hilfe'")
            
