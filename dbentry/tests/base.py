import contextlib
import sys
import warnings
from importlib import import_module
from unittest.mock import Mock

from django import forms
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
        try:
            yield
        except exceptions as e:
            fail_txt = "{} raised.".format(e.__class__.__name__)
            if msg:
                fail_txt += '\n' + msg
            self.fail(fail_txt)

    def assertSelect2JS(self, js, jquery='', select2='', jquery_init=''):
        """
        Assert that select2 is loaded after jQuery and before jquery_init.

        Arguments:
            js (iterable): the iterable containing the javascript URLs
            jquery/select2/jquery_init (str): URLs to the javascript resources
        Pass None to either jquery or select2 to skip the assertions.
        """
        if jquery is None or select2 is None:
            return
        from django.conf import settings
        extra = '' if settings.DEBUG else '.min'
        if jquery == '':
            jquery = 'admin/js/vendor/jquery/jquery%s.js' % extra
        if select2 == '':
            # Note that dal always loads select2.full.js regardless of
            # settings.DEBUG.
            select2 = 'admin/js/vendor/select2/select2.full.js'
        if jquery_init == '':
            jquery_init = 'admin/js/jquery.init.js'

        self.assertIn(jquery, js, msg="select2 requires jQuery.")
        self.assertIn(select2, js, msg="select2 js file not found.")
        self.assertGreater(
            js.index(select2), js.index(jquery),
            msg="select2 must be loaded after jQuery."
        )
        if jquery_init:  # jquery_init could be None
            self.assertIn(jquery_init, js)
            self.assertGreater(
                js.index(jquery_init), js.index(select2),
                msg="select2 must be loaded before django's jquery_init."
            )


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
            username='noperms', password='Boop')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]

    def setUp(self):
        super(UserTestCase, self).setUp()
        self.client.force_login(self.super_user)  # super_user logged in by default


class RequestTestCase(UserTestCase):

    path = ''

    def get_path(self):
        return self.path

    def get_response(self, method, path, data=None, user=None, **kwargs):
        self.client.force_login(user or self.super_user)
        if method == 'GET':
            func = self.client.get
        elif method == 'POST':
            func = self.client.post
        else:
            raise ValueError("Unknown request method: %s" % method)
        return func(path or self.get_path(), data, **kwargs)

    def post_request(self, path=None, data=None, user=None, **kwargs):
        return self.get_response('POST', path, data, user, **kwargs).wsgi_request

    def get_request(self, path=None, data=None, user=None, **kwargs):
        return self.get_response('GET', path, data, user, **kwargs).wsgi_request

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
        super().setUpTestData()

        if not cls.changelist_path:
            cls.changelist_path = reverse(
                'admin:DBentry_{}_changelist'.format(cls.model._meta.model_name))
        if not cls.change_path:
            cls.change_path = unquote(reverse(
                'admin:DBentry_{}_change'.format(cls.model._meta.model_name), args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse('admin:DBentry_{}_add'.format(cls.model._meta.model_name))

    def setUp(self):
        super().setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)

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
