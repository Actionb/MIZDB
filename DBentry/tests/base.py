import contextlib
import sys
import warnings
from importlib import import_module
from unittest.mock import Mock

from django import forms
from django.contrib.admin import helpers
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.conf import settings
from django.conf.urls import url, include
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.http import unquote

from DBentry.tests.mixins import CreateFormMixin, CreateViewMixin, TestDataMixin
from DBentry.sites import miz_site


def _showwarning(message, category=Warning, *args, **kwargs):
    message = category.__name__ + ': ' + str(message)
    print(message, file=sys.stderr, end='... ')


if not sys.warnoptions:
    import os
    # Change the filter in this process
    warnings.simplefilter("always")
    os.environ["PYTHONWARNINGS"] = "always"  # Also affect subprocesses
    warnings.showwarning = _showwarning


def mockv(value, **kwargs):
    return Mock(return_value=value, **kwargs)


@contextlib.contextmanager
def override_urls(url_patterns):
    dummy_module = type(
        'Dummy',
        (object, ),
        {'urlpatterns': url_patterns}
    )  # creating a dummy module is safer than using a basic Mock object
    with override_settings(ROOT_URLCONF=dummy_module):
        yield


@contextlib.contextmanager
def add_urls(url_patterns, regex=''):
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
    warnings = 'always'
    def warn(self, message):
        warnings.warn(message)

    @contextlib.contextmanager
    def assertNotRaises(self, exceptions, msg=None):
        """Assert that the body does NOT raise one of the passed exceptions."""
        # NOTE: what if the body raises more than one exception?
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


class DataTestCase(TestDataMixin, MyTestCase):

    def assertQuerysetEqual(self, queryset, values, transform=repr, ordered=False, msg=None):
        # django's assertQuerysetEqual does not transform 'values' if it would be required
        if isinstance(values, QuerySet):
            values = map(transform, values)
        return super().assertQuerysetEqual(queryset, values, transform, ordered, msg)


class UserTestCase(MyTestCase):

    @classmethod
    def setUpTestData(cls):
        super(UserTestCase, cls).setUpTestData()
        cls.super_user = User.objects.create_superuser(
            username='superuser', email='testtest@test.test', password='test1234')
        cls.staff_user = User.objects.create_user(
            username='staff', password='Stuff', is_staff=True)
        cls.noperms_user = User.objects.create_user(
            username='Beep', password='Boop')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]

    def setUp(self):
        super(UserTestCase, self).setUp()
        self.client.force_login(self.super_user)  # super_user logged in by default


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
        error_msg = "Message {} not found in messages: {}".format(
            expected_message, [m[:len(expected_message) + 5] + "[...]" for m in messages])
        if not any(m.startswith(expected_message) for m in messages):
            raise AssertionError(error_msg)

    def assertMessageNotSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(
            expected_message,  [m[:len(expected_message) + 5] + "[...]" for m in messages])
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
            cls.changelist_path = reverse(
                'admin:DBentry_{}_changelist'.format(cls.model._meta.model_name))
        if not cls.change_path:
            cls.change_path = unquote(reverse(
                'admin:DBentry_{}_change'.format(cls.model._meta.model_name), args=['{pk}']))
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

    def call_action(self, action_name, objs, data=None):
        if isinstance(objs, QuerySet):
            objs = objs.values_list('pk', flat=True)
        request_data = {'action': action_name, helpers.ACTION_CHECKBOX_NAME: objs}
        for other_dict in data or []:
            request_data.update(other_dict)
        return self.client.post(self.changelist_path, data=request_data)

    def get_changelist(self, request):
        return self.model_admin.get_changelist_instance(request)

    def get_queryset(self, request=None):
        if request is None:
            request = self.get_request(path=self.changelist_path)
        return self.model_admin.get_queryset(request)


##############################################################################################################
# TEST_FORMS TEST CASES
##############################################################################################################
class FormTestCase(MyTestCase, CreateFormMixin):

    def assertFormValid(self, form):
        if not form.is_valid():
            form_errors = [(k, v) for k, v in form.errors.items()]
            raise AssertionError(
                'Form invalid. Form errors: {}'.format(form_errors))

    def assertFormInvalid(self, form):
        if form.is_valid():
            raise AssertionError('Form valid when expected to be invalid')


class ModelFormTestCase(TestDataMixin, FormTestCase):

    fields = None

    def get_form(self, **kwargs):
        return forms.modelform_factory(
            self.model, form=self.form_class, fields=self.fields)(**kwargs)
