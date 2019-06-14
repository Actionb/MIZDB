from ..base import MyTestCase, AdminTestCase

from unittest import mock

from django import forms

from DBentry import models as _models, admin as _admin
from DBentry.search.admin import AdminSearchFormMixin, ChangelistSearchFormMixin

class TestAdminMixin(AdminTestCase):
    
    model = _models.bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    
    def setUp(self):
        super().setUp()
        # Check if model_admin_class inherits from AdminSearchFormMixin.
        # setUp() isn't quite the right place to do it (setUp runs for every test),
        # but I couldn't be bothered.
        msg = "'%s' does not inherit from '%s'" % (
            self.model_admin_class.__name__, AdminSearchFormMixin.__name__)
        self.assertIsInstance(self.model_admin, AdminSearchFormMixin, msg = msg)
    
    @mock.patch('DBentry.search.admin.searchform_factory')
    def test_get_search_form_class(self, mocked_factory):
        # Test that a custom search_form_class is prioritized:
        self.model_admin.search_form_class = 1
        self.assertEqual(self.model_admin.get_search_form_class(), 1)
        
        # Test the default way:
        self.model_admin.search_form_class = None
        self.model_admin.search_form_kwargs = {'fields': 'datum'}
        self.model_admin.get_search_form_class(labels ={'datum': 'Das Datum!'})
        self.assertTrue(mocked_factory.called)
        args, kwargs = mocked_factory.call_args
        expected = {'fields': 'datum', 'labels': {'datum': 'Das Datum!'}}
        for key, value in expected.items():
            with self.subTest():
                self.assertIn(key, kwargs)
                self.assertEqual(kwargs[key], value)
            
    def test_get_search_form_with_wrapper(self):
        # Assert that the search form is wrapped in a wrapper declared by search_form_wrapper attribute.
        def dummy_wrapper(form):
            setattr(form, 'formwaswrapped', True)
            return form
        
        with mock.patch.object(self.model_admin, 'get_search_form_class') as mocked_form_class:
            mocked_form_class.return_value = type('Dummy', (forms.Form, ), {})
            self.model_admin.search_form_wrapper = dummy_wrapper
            form = self.model_admin.get_search_form()
            self.assertTrue(hasattr(form, 'formwaswrapped'))        
    
    def test_search_form_added_to_response_context(self):
        # Assert that the changelist_view's response context contains 'advanced_search_form'.
        response = self.client.get(path = self.changelist_path)
        self.assertIn('advanced_search_form', response.context)
    
# ChangelistSearchFormMixin inherits from object but calls
# super().get_filters_params; object cannot be patched!
# create some dummy class to set up a fitting inheritance.
class DummyParent(object):
    def get_filters_params(self, *args, **kwargs):
        pass
    
@mock.patch.object(DummyParent, 'get_filters_params')
class TestChangelistMixin(MyTestCase):
    
    def get_dummy_changelist(self, bases = None, attrs = None):
        bases = bases or (ChangelistSearchFormMixin, DummyParent)
        attrs = attrs or {}
        return type('Changelist', bases, attrs)
    
    def test_get_filters_params(self, super_get_params):
        initial_params = {'seite': '1', 'genre__genre': 1, 'somethingelse': 0}
        super_get_params.return_value = initial_params

        mocked_form = mock.Mock()
        mocked_form.fields = ['seite', 'genre__genre']
        mocked_form.get_filter_params.return_value = {'seite': 1, 'genre__genre': 2}
        
        mocked_model_admin = mock.Mock()
        mocked_model_admin.get_search_form.return_value = mocked_form
        
        changelist = self.get_dummy_changelist(attrs = {'model_admin': mocked_model_admin})()
        params = changelist.get_filters_params(initial_params)
        # params should be updated by get_filter_params.return_value while 
        # retaining any other params (somethingelse).
        expected = {'seite': 1, 'genre__genre': 2, 'somethingelse': 0}
        for key, value in expected.items():
            with self.subTest():
                self.assertIn(key, params)
                self.assertEqual(params[key], value)
        self.assertEqual(len(expected), len(params))
        
    def test_get_filters_params_removes_form_fields_from_params(self, super_get_params):
        # Assert that any params connected to fields of the form 
        # are removed if the formfield's values are empty/invalid.
        initial_params = {'seite': '1'}
        super_get_params.return_value = initial_params

        mocked_form = mock.Mock()
        mocked_form.fields = ['seite', 'somethingelse']
        mocked_form.get_filter_params.return_value = {}
        
        mocked_model_admin = mock.Mock()
        mocked_model_admin.get_search_form.return_value = mocked_form
        
        changelist = self.get_dummy_changelist(attrs = {'model_admin': mocked_model_admin})()
        self.assertNotIn('seite', changelist.get_filters_params(initial_params))
        
    def test_get_filters_params_returns_params_on_exception(self, super_get_params):
        # Assert that get_filters_params returns the initial params upon 
        # encountering an AttributeError when trying to call the model admin's
        # get_search_form method.
        super_get_params.return_value = 'Foobar'
        params = self.get_dummy_changelist()().get_filters_params(params = 'Beepboop')
        self.assertEqual(params, 'Foobar')
        
