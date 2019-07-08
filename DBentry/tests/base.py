from unittest.mock import Mock
import contextlib
import warnings

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.http import unquote
from django.db.models.query import QuerySet

from DBentry.sites import miz_site

from .mixins import CreateFormMixin, CreateViewMixin, TestDataMixin

from django import forms

import sys

def _showwarning(message, category = Warning, *args, **kwargs):
    message = category.__name__ + ': ' + str(message)
    print(message, file = sys.stderr, end='... ')
    
if not sys.warnoptions:
    import os
    warnings.simplefilter("always") # Change the filter in this process #TODO: check out TextTestRunner.warnings attribute 
    os.environ["PYTHONWARNINGS"] = "always" # Also affect subprocesses
    warnings.showwarning = _showwarning


def mockv(value, **kwargs):
    return Mock(return_value=value, **kwargs)
    
def mockex(exception, **kwargs):
    return Mock(side_effect=exception, **kwargs)
    
@contextlib.contextmanager
def override_urls(url_patterns):
    dummy_module = type('Dummy', (object, ), {'urlpatterns':url_patterns}) # safer than using a basic Mock object
    with override_settings(ROOT_URLCONF=dummy_module): 
        yield
        
@contextlib.contextmanager
def add_urls(url_patterns, regex=''):
    from django.conf import settings
    from django.conf.urls import url, include
    from importlib import import_module
    try:
        urls = import_module(settings.ROOT_URLCONF).urlpatterns
    except AttributeError as e:
        raise AttributeError(e.args[0], "Cannot override ROOT_URLCONF twice!")
    urls.insert(0, url(regex, include(url_patterns)))
    with override_urls(urls):
        yield
        
class TestNotImplementedError(AssertionError):
    pass

class MyTestCase(TestCase):
    
    def warn(self, message):
        warnings.warn(message)
    
    @contextlib.contextmanager
    def collect_fails(self, msg = None):
        #TODO: documentation
        #TODO: check out unittest.case.TestCase.subTest
        collected = []
        @contextlib.contextmanager
        def decorator(*args, **kwargs):
            try:
                yield
            except AssertionError as e:
                collected.append((e, args, kwargs))
                
        yield decorator
        
        if collected:
            fail_txt = "Collected errors:"
            template = "\nError: {error}"
            if collected[0][1] or collected[0][2]:
                # Add args and/or kwargs to the error output, if they contain any data
                # All items in collected have the same number of args or the same keywords, so we only need to check the first item
                template += "\ncollected with args: {args} | kwargs: {kwargs}"
            if msg:
                fail_txt = msg + '\n' + fail_txt
            for e, args, kwargs in collected:
                fail_txt += template.format(error=e, args=args, kwargs=kwargs)
            self.fail(fail_txt)
                
            
    @contextlib.contextmanager
    def assertNotRaises(self, exceptions, msg = None):
        """
        Assert that the body does NOT raise one of the passed exceptions.
        """ 
        #NOTE: what if the body raises more than one exception?
        raised = None
        try:
            yield
        except Exception as e:
            raised = e
            
        if raised and issubclass(raised.__class__, exceptions):
            fail_txt = "{} raised.".format(raised.__class__.__name__)
            if msg:
                fail_txt += ':' + msg
            self.fail(fail_txt)
    #NOTE: only the bulk tests use these dict assertions
    def assertDictKeysEqual(self, d1, d2):
        t = "dict keys missing from {d}: {key_diff}"
        msg = ''
        key_diff = set(d1.keys()) - set(d2.keys())
        if key_diff:
            msg = t.format(d='d2', key_diff=str(key_diff))
        
        key_diff = set(d2.keys()) - set(d1.keys())
        if key_diff:
            if msg:
                msg += '\n'
            msg +=  t.format(d='d1', key_diff=str(key_diff))
        if msg:
            raise AssertionError(msg)
    
    def assertDictsEqual(self, dict1, dict2, msg=''):
        from django.http.request import QueryDict
        d1 = dict1.copy()
        d2 = dict2.copy()
        if isinstance(d1, QueryDict) and not isinstance(d2, QueryDict) or isinstance(d2, QueryDict) and not isinstance(d1, QueryDict):
            for d in [d1, d2]:
                # forcefully convert QueryDicts
                try:
                    d = d.dict()
                except:
                    continue
        self.assertDictKeysEqual(d1, d2)
        
        t = "dict values differ for key {k}: \n{v1} \n!=\n{v2}\n\n\n"
        msg = ''
        for k, v in d1.items():
            v1 = v
            v2 = d2.get(k)
            if isinstance(v1, dict) and isinstance(v2, dict):
                try:
                    self.assertDictsEqual(v1, v2)
                except AssertionError as e:
                    msg += "subdicts for key {k} differ: {msg}\n\n\n".format(k=k, msg=e.args[0])
            else:
                v1 = str(v1)
                v2 = str(v2)
                if v1 != v2:
                    msg += t.format(k=k, v1=v1, v2=v2)
        if msg:
            raise AssertionError(msg)
    
    def assertListEqualSorted(self, list1, list2, msg=None):
        self.assertListEqual(sorted(list1), sorted(list2), msg)
     
    #NOTE: no test uses this assertion
    def assertAllValues(self, values_list, value, msg=None):
        """
        Assert that `value` is equal to all items of `values_list`.
        """
        expected = [value for v in values_list]
        self.assertEqual(values_list, expected, msg)  # delivers more useful information on failure than self.assertTrue(all(v==value for v in values_list))
      
class DataTestCase(TestDataMixin, MyTestCase):
    
    # django's assertQuerysetEqual will transform the queryset's values according to function given by parameter `transform` (assertQuerysetEqual requires hashable objects).
    # This would end up converting dicts/tuples from queryset.values()/.values_list() into strings.
    # Obviously, this is not what we want, if we want to make comparing queryset.values()/.values_list() simple to use.
    # We could pass transform = lambda d: tuple(*d.items()) to assertQuerysetEqual, but that would require transforming `values` as well.
    
    def assertQSEqual(self, queryset, values, transform=str, ordered=False, msg=None):
        # Reconfiguration of the default parameters to values we use most in tests: reduces clutter
        # - the __str__ method is heavily used in our app, more than repr
        # - the tests usually do not care about the order of values
        if not isinstance(values, (list, tuple)):
            values = [values]
        self.assertQuerysetEqual(queryset, values, transform, ordered, msg)
        
    def assertQuerysetEqual(self, queryset, values, transform=repr, ordered=False, msg=None):
        # django's assertQuerysetEqual does not transform 'values' if it would be required
        if isinstance(values, QuerySet):
            values = map(transform, values)
        return super().assertQuerysetEqual(queryset, values, transform, ordered, msg)
        
    def assertPKListEqual(self, pk_list1, pk_list2):
        if isinstance(pk_list1, QuerySet):
            pk_list1 = list(pk_list1.values_list('pk', flat=True))
        if isinstance(pk_list2, QuerySet):
            pk_list2 = list(pk_list2.values_list('pk', flat=True))
        self.assertListEqualSorted(pk_list1, pk_list2)
    
    #NOTE: only test_manager cases use assertQSValues
    def assertQSValues(self, queryset, fields, values, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(values, (list, tuple)):
            # A list of tuples of (field, value) is expected.
            values = list(zip(fields, [values]*len(fields)))
            
        # Still call queryset.values(), but convert the results from a list of dicts to a list of tuples for easier comparison.
        qs_list = [tuple(*i.items()) for i in queryset.values(*fields)]
        self.assertListEqualSorted(qs_list, values, msg)
        
    def assertAllQSValues(self, queryset, fields, value, msg=None):
        from collections import Iterable
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(value, str) or not isinstance(value, Iterable):
            if len(fields)==1:
                value = (fields, value)
            else:
                raise TypeError("argument value must be an iterable")
                
        expected = [value] * queryset.count() if queryset.count() else [value]  # an empty queryset should assert as not equal to [value] and not as equal to [] 
        self.assertQSValues(queryset, fields, expected, msg)
    
    #NOTE: test_signals, test_query,test_models, test_manager use these two
    def assertQSValuesList(self, queryset, fields, values, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(values, (list, tuple)):
            values = [values]
        values_list = list(queryset.values_list(*fields, flat=len(fields)==1))
        self.assertListEqualSorted(values_list, values, msg)
        
    def assertAllQSValuesList(self, queryset, fields, value, transform=str, ordered=False, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        expected = [value] * queryset.count() if queryset.count() else [value]  # an empty queryset should assert as not equal to [value] and not as equal to [] 
        self.assertQSValuesList(queryset, fields, expected, msg)
        
         
class UserTestCase(MyTestCase):
    
    @classmethod
    def setUpTestData(cls):
        super(UserTestCase, cls).setUpTestData()
        cls.super_user = User.objects.create_superuser(username='superuser', email='testtest@test.test', password='test1234')
        cls.staff_user = User.objects.create_user(username='staff', password='Stuff', is_staff = True)
        cls.noperms_user = User.objects.create_user(username='Beep', password='Boop')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]
        
    def setUp(self):
        super(UserTestCase, self).setUp()
        self.client.force_login(self.super_user) # super_user logged in by default

class RequestTestCase(UserTestCase):
    
    path = ''
    
    def get_path(self):
        return self.path
    
    def post_request(self, path=None, data=None, user=None, **kwargs):
        self.client.force_login(user or self.super_user)
        return self.client.post(path or self.get_path(), data, **kwargs).wsgi_request
    
    def get_request(self, path=None, data=None, user=None, **kwargs):
        self.client.force_login(user or self.super_user)
        return self.client.get(path or self.get_path(), data, **kwargs).wsgi_request
        
    def assertMessageSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} not found in messages: {}".format(expected_message,  [m[:len(expected_message)+5] + "[...]" for m in messages])
        if not any(m.startswith(expected_message) for m in messages):
            raise AssertionError(error_msg)
        #self.assertTrue(any(m.startswith(expected_message) for m in messages), error_msg)
        
    def assertMessageNotSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(expected_message,  [m[:len(expected_message)+5] + "[...]" for m in messages])
        if any(m.startswith(expected_message) for m in messages):
            raise AssertionError(error_msg)
        
    
class ViewTestCase(RequestTestCase, CreateViewMixin):
        pass
        
class AdminTestCase(TestDataMixin, RequestTestCase):
    
    admin_site = miz_site
    model_admin_class = None
    
    changelist_path = ''
    change_path = ''
    add_path = ''
    
    @classmethod
    def setUpTestData(cls):
        super(AdminTestCase, cls).setUpTestData()
            
        if not cls.changelist_path:
            cls.changelist_path = reverse('admin:DBentry_{}_changelist'.format(cls.model._meta.model_name))
        if not cls.change_path:
            cls.change_path = unquote(reverse('admin:DBentry_{}_change'.format(cls.model._meta.model_name), args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse('admin:DBentry_{}_add'.format(cls.model._meta.model_name))
    
    def setUp(self):
        super(AdminTestCase, self).setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)
        
    def get_action_func(self, action_name):
        for action in self.model_admin.actions: 
            func, name, desc = self.model_admin.get_action(action) 
            if name == self.action:
                return func 
        
    def call_action(self, action_name, objs, data=[]):
        if isinstance(objs, QuerySet):
            objs = objs.values_list('pk', flat=True)
        from django.contrib.admin import helpers    
        request_data = {'action':action_name, helpers.ACTION_CHECKBOX_NAME : objs}
        for other_dict in data:
            request_data.update(other_dict)
        return self.client.post(self.changelist_path, data=request_data)
        
    def get_changelist(self, request):
        return self.model_admin.get_changelist_instance(request)
        #TODO: remove this unreachable code below
        list_display = self.model_admin.get_list_display(request)
        list_display_links = self.model_admin.get_list_display_links(request, list_display)
        list_filter = self.model_admin.get_list_filter(request)
        search_fields = self.model_admin.get_search_fields(request)
        list_select_related = self.model_admin.get_list_select_related(request)
        sortable_by = self.model_admin.get_sortable_by(request)
        
        ChangeList = self.model_admin.get_changelist(request)
        cl = ChangeList(
            request, self.model_admin.model, list_display,
            list_display_links, list_filter, self.model_admin.date_hierarchy,
            search_fields, list_select_related, self.model_admin.list_per_page,
            self.model_admin.list_max_show_all, self.model_admin.list_editable, self.model_admin, 
            sortable_by
        )
        return cl
        

##############################################################################################################
# TEST_FORMS TEST CASES
##############################################################################################################
class FormTestCase(MyTestCase, CreateFormMixin):
    
    def assertFormValid(self, form):
        if not form.is_valid():
            raise AssertionError('Form invalid. Form errors: {}'.format([(k,v) for k,v in form.errors.items()]))
            
    def assertFormInvalid(self, form):
        if form.is_valid():
            raise AssertionError('Form valid when expected to be invalid')
            
class ModelFormTestCase(TestDataMixin, FormTestCase):
    
    fields = None
    
    def get_form(self, **kwargs):
        return forms.modelform_factory(self.model, form=self.form_class, fields=self.fields)(**kwargs)
        
