from .base import HelpViewMixin, ModelHelpViewTestCase
from ..base import ViewTestCase

from DBentry.models import artikel, buch
from DBentry.admin import ArtikelAdmin
from DBentry.help.helptext import ModelAdminHelpText, FormViewHelpText
from DBentry.help.views import HelpIndexView, BaseHelpView, FormHelpView, ModelAdminHelpView

from DBentry.base.views import MIZAdminPermissionMixin as target_view_base #NOTE: update this if you change FormHelpView.permission_test check to issubclass(UserPassesTestMixin)

class TestHelpIndexView(HelpViewMixin, ViewTestCase):
    
    path = '/admin/help/'
    view_class = HelpIndexView
    
    def test_get_context_data_forms(self):
        form_help1 = type(
            'FormHelp1', (FormViewHelpText, ), {
                'form_class': 'so_lazy', # This will determine the index_title for form_help1
                'target_view_class': self.get_dummy_view_class(bases = target_view_base, attrs = {'permission_test': lambda request: request.user.is_superuser}), 
            }
        )
        form_help2 = type(
            'FormHelp2', (FormViewHelpText, ), {
                'index_title': 'TestingForms', 
                'form_class': 'so_lazy',
                'target_view_class': self.get_dummy_view_class(bases = target_view_base, attrs = {'permission_test': lambda request: request.user.is_superuser}), 
            }
        )
        self.registry.register(helptext = form_help1, url_name = None)
        self.registry.register(helptext = form_help2, url_name = 'help_boop')
        self.assertEqual(len(self.registry._registry), 2)
        
        view = self.get_view(request = self.get_request(user = self.noperms_user), registry = self.registry)
        context = view.get_context_data()
        self.assertIn('form_helps', context)
        self.assertEqual(context['form_helps'], [], msg = "User without any permissions should not have access to any form helps.")
        
        with self.add_urls():
            view = self.get_view(request = self.get_request(path=''), registry = self.registry)
            context = view.get_context_data()
            self.assertIn('form_helps', context)
            form_helps = context['form_helps']
            self.assertEqual(len(form_helps), 2)
            
            html_template = '<a href="{url}{popup}">{label}</a>' 
            expected = html_template.format(url = '/admin/help/DummyView/', popup = '', label = 'Hilfe für so_lazy')
            self.assertEqual(form_helps[0], expected)
            expected = html_template.format(url = '/admin/help/boop/', popup = '', label = 'TestingForms')
            self.assertEqual(form_helps[1], expected)
            
            # As a popup
            view = self.get_view(request = self.get_request(path = self.path + '?_popup=1'), registry = self.registry)
            context = view.get_context_data()
            self.assertIn('form_helps', context)
            form_helps = context['form_helps']
            self.assertEqual(len(form_helps), 2)

            expected = html_template.format(url = '/admin/help/DummyView/', popup = '?_popup=1', label = 'Hilfe für so_lazy')
            self.assertEqual(form_helps[0], expected)
            expected = html_template.format(url = '/admin/help/boop/', popup = '?_popup=1', label = 'TestingForms')
            self.assertEqual(form_helps[1], expected)
    
    def test_get_context_data_models(self):
        artikel_help = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
        buch_help = type('BuchHelpText', (ModelAdminHelpText, ), {'model':buch, 'index_title':'Beep'})
        self.registry.register(helptext = artikel_help, url_name = None)
        self.registry.register(helptext = buch_help, url_name = None)
        
        view = self.get_view(request = self.get_request(user = self.noperms_user), registry = self.registry)
        context = view.get_context_data()
        self.assertIn('model_helps', context)
        self.assertEqual(context['model_helps'], [], msg = "User without any model permissions should not have access to any model helps.")
        
        with self.add_urls():
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
        dummy_target_view = self.get_dummy_view_class(bases = target_view_base, attrs = {'permission_test': lambda request: request.user.is_superuser })
        request = self.get_request(user = self.noperms_user)
        self.assertFalse(self.view_class.permission_test(request, dummy_target_view))
        
        request = self.get_request(user = self.super_user)
        self.assertTrue(self.view_class.permission_test(request, dummy_target_view))

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
            
