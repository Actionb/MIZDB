from .base import *

from DBentry.help.views import HelpIndexView, FormHelpView, ModelAdminHelpView
from DBentry.help.helptext import BaseHelpText, ModelAdminHelpText, FormViewHelpText
from DBentry.help.registry import register
from DBentry.utils import get_model_admin_for_model

class TestRegisterDecorator(MyTestCase):
    
    def test_wrappper(self):
        # Assert that the wrapper only allows subclasses of BaseHelpText / HelpRegistry
        with self.assertRaises(ValueError):
            register()(str)
        with self.assertRaises(ValueError):
            register(registry = "not a registry!")(BaseHelpText)
        

class TestHelpRegistry(HelpRegistryMixin, MyTestCase):
    
    def test_help_url_for_view(self):
        # Assert that help_url_for_view returns the correct path or an empty string
        modeladmin_helptext = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
        self.registry.register(modeladmin_helptext, url_name = None)
        # Get the right ModelAdmin instance for the lookup
        registered_model_admin = get_model_admin_for_model(artikel)
        # Get a ModelAdmin instance that does not have a registered helptext
        unregistered_model_admin = get_model_admin_for_model(sender)
        with self.add_urls():
            self.assertEqual(self.registry.help_url_for_view(registered_model_admin), '/admin/help/artikel/')
            self.assertEqual(self.registry.help_url_for_view(unregistered_model_admin), '')
            
    def test_get_urls(self):
        from DBentry.bulk.views import BulkAusgabe
        modeladmin_helptext = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
        formview_helptext = type('BulkFormHelpText', (FormViewHelpText, ), {'target_view_class': BulkAusgabe})
        self.registry.register(modeladmin_helptext, url_name = None)
        self.registry.register(formview_helptext, url_name = 'help_bulk')
        
        urls = self.registry.get_urls()
        self.assertEqual(len(urls), 3)
        
        modeladmin_pattern, formview_pattern, index_pattern = urls
        
        # MODELADMIN PAGE
        self.assertEqual(modeladmin_pattern._regex, r'^artikel/')
        self.assertEqual(modeladmin_pattern.name, 'help_artikel')
        self.assertEqual(modeladmin_pattern.callback.view_class, ModelAdminHelpView)
        expected_kwargs = {
            'registry': self.registry, 
            'helptext_class': modeladmin_helptext, 
            'model_admin': get_model_admin_for_model(artikel)
        }
        self.assertEqual(modeladmin_pattern.callback.view_initkwargs, expected_kwargs)
        
        # FORMVIEW PAGE
        self.assertEqual(formview_pattern._regex, r'^bulk/')
        self.assertEqual(formview_pattern.name, 'help_bulk')
        self.assertEqual(formview_pattern.callback.view_class, FormHelpView)
        expected_kwargs = {
            'helptext_class': formview_helptext, 
            'target_view_class': BulkAusgabe
        }
        self.assertEqual(formview_pattern.callback.view_initkwargs, expected_kwargs)
        
        # INDEX PAGE
        self.assertEqual(index_pattern._regex, '')
        self.assertEqual(index_pattern.name, 'help_index')
        self.assertEqual(index_pattern.callback.view_class, HelpIndexView)
        expected_kwargs = {
            'registry': self.registry, 
        }
        self.assertEqual(index_pattern.callback.view_initkwargs, expected_kwargs)
        
    
    def test_register(self):
        modeladmin_helptext = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
        # Make sure we get the *same* instance of the ModelAdmin
        model_admin = get_model_admin_for_model(artikel)
        self.registry.register(modeladmin_helptext, url_name = None)
        self.assertIn(model_admin, self.registry._registry)
        self.assertEqual(self.registry._registry[model_admin], (modeladmin_helptext, 'help_artikel'))
        self.assertIn(model_admin, self.registry._modeladmins)
        
        self.registry.register(modeladmin_helptext, url_name = 'help_test')
        self.assertIn(model_admin, self.registry._registry)
        self.assertEqual(self.registry._registry[model_admin], (modeladmin_helptext, 'help_test'))

        formview_helptext_target = type('TargetView', (object, ), {'form_class':'just cheating'})
        formview_helptext = type('SomeFormHelpText', (FormViewHelpText, ), {'target_view_class':formview_helptext_target})
        self.registry.register(formview_helptext, url_name = None)
        self.assertIn(formview_helptext_target, self.registry._registry)
        self.assertEqual(self.registry._registry[formview_helptext_target], (formview_helptext, "help_TargetView"))
        self.assertIn(formview_helptext_target, self.registry._formviews)
        
        self.registry.register(formview_helptext, url_name = 'help_test')
        self.assertEqual(self.registry._registry[formview_helptext_target], (formview_helptext, 'help_test'))
        
        formview_helptext.target_view_class = None
        with self.assertRaises(AttributeError) as e:
            self.registry.register(formview_helptext, url_name = None)
            self.assertEqual(e.args, ("Helptext class has no target_view_class set.", formview_helptext))
            
        with self.assertRaises(TypeError) as e:
            self.registry.register("this should not work", url_name = None)
            self.assertEqual(e.args, ("Unknown helptext class:", "this should not work"))
        
