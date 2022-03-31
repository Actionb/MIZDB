import contextlib
import sys
import warnings
from importlib import import_module
from unittest.mock import Mock

from django import forms
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.conf import settings
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings
from django.urls import path, reverse
from django.utils.http import unquote

from dbentry.sites import miz_site

# Display all warnings:
if not sys.warnoptions:
    import os
    warnings.simplefilter("default")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "default"  # Also affect subprocesses


def mockv(value, **kwargs):  # TODO: remove: be explicit in tests
    return Mock(return_value=value, **kwargs)


@contextlib.contextmanager
def override_urls(url_patterns):
    """
    Replace the url patterns of the root URLconf with the given list of URL
    patterns.
    """
    class Dummy:
        urlpatterns = url_patterns
    with override_settings(ROOT_URLCONF=Dummy):
        yield


@contextlib.contextmanager
def add_urls(url_patterns, route=''):
    """Inject the given URL patterns into the root URLconf."""
    try:
        # noinspection PyUnresolvedReferences
        urls = import_module(settings.ROOT_URLCONF).urlpatterns[:]
    except AttributeError as e:
        raise AttributeError(e.args[0], "No 'urlpatterns' in ROOT_URLCONF.")
    urls.insert(0, path(route, url_patterns))
    with override_urls(urls):
        yield


class TestNotImplementedError(AssertionError):  # TODO: remove: not used
    pass


class MIZTestCase(TestCase):

    warnings = 'always'  # FIXME: what does this do? Does it override the warning filter ("default")?

    @staticmethod
    def warn(message):  # TODO: remove: be explicit in tests / also not used
        warnings.warn(message)

    @contextlib.contextmanager
    def assertNotRaises(self, exceptions, msg=None):
        """Assert that the body does NOT raise one of the passed exceptions."""
        try:
            yield
        except exceptions as e:
            self.fail(self._formatMessage(msg, f"{e.__class__.__name__} raised."))

    # noinspection PyIncorrectDocstring
    def assertSelect2JS(self, js, jquery='', select2='', jquery_init=''):  # TODO: remove: only used once
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


class DataTestCase(MIZTestCase):

    model = None
    queryset = None
    test_data = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        if cls.test_data is None:
            cls.test_data = []

    def setUp(self):
        super().setUp()
        # Refresh each test_data instance and prepare an instance-only queryset
        # for each instance.
        for c, obj in enumerate(self.test_data, 1):
            obj.refresh_from_db()  # TODO: is this even necessary?
            setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk))
        self.queryset = self.model.objects.all()

    def assertQuerysetEqual(self, queryset, values, transform=repr, ordered=False, msg=None):
        # TODO: remove: not used
        # django's assertQuerysetEqual does not transform 'values' if it would be required
        if isinstance(values, QuerySet):
            values = map(transform, values)
        return super().assertQuerysetEqual(queryset, values, transform, ordered, msg)


class UserTestCase(MIZTestCase):

    super_user = None
    staff_user = None
    noperms_user = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.super_user = User.objects.create_superuser(
            username='superuser', email='testtest@test.test', password='foobar')
        cls.staff_user = User.objects.create_user(
            username='staff', password='foo', is_staff=True)
        cls.noperms_user = User.objects.create_user(
            username='noperms', password='bar')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]

    def setUp(self):
        super().setUp()
        # Have the super_user be logged in by default:
        self.client.force_login(self.super_user)


class RequestTestCase(UserTestCase):
    # TODO: use RequestFactory (instead of client) for get_request/post_request.
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

    def assertMessageSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} not found in messages: {}".format(
            expected_message, [m[:len(expected_message) + 5] + "[...]" for m in messages])
        if not any(m.startswith(expected_message) for m in messages):
            self.fail(self._formatMessage(msg, error_msg))

    def assertMessageNotSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(
            expected_message, [m[:len(expected_message) + 5] + "[...]" for m in messages])
        if any(m.startswith(expected_message) for m in messages):
            self.fail(self._formatMessage(msg, error_msg))


class ViewTestCase(RequestTestCase):

    view_class = None

    def get_view(self, request=None, args=None, kwargs=None, **initkwargs):
        """Instantiate and set up the view without calling dispatch()."""
        # TODO: rework the arguments?
        #  Make initkwargs a keyword argument and then just use *args, **kwargs?
        view = self.view_class(**initkwargs)
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        view.setup(request, *args, **kwargs)
        return view

    def get_dummy_view_class(self, bases=None, attrs=None):
        # TODO: is it necessary to keep this (and get_dummy_view)?
        if bases is None:
            bases = getattr(self, 'view_bases', ())
        if attrs is None:
            attrs = attrs or getattr(self, 'view_attrs', {})
        if not isinstance(bases, (list, tuple)):
            bases = (bases,)
        return type("DummyView", bases, attrs)

    def get_dummy_view(self, bases=None, attrs=None, **initkwargs):
        return self.get_dummy_view_class(bases, attrs)(**initkwargs)


class AdminTestCase(DataTestCase, RequestTestCase):
    admin_site = miz_site  # TODO: use AdminSite()? less sensitive/more agnostic/decoupled
    model_admin_class = None

    changelist_path = ''
    change_path = ''
    add_path = ''

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        if not cls.changelist_path:
            cls.changelist_path = reverse(
                'admin:dbentry_{}_changelist'.format(cls.model._meta.model_name))
        if not cls.change_path:
            cls.change_path = unquote(reverse(
                'admin:dbentry_{}_change'.format(cls.model._meta.model_name), args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse('admin:dbentry_{}_add'.format(cls.model._meta.model_name))

    def setUp(self):
        super().setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)

    def get_changelist(self, request):
        return self.model_admin.get_changelist_instance(request)

    def get_queryset(self, request=None):
        if request is None:
            request = self.get_request(path=self.changelist_path)
        return self.model_admin.get_queryset(request)


class FormTestCase(MIZTestCase):  # TODO: remove; use explicit dummy forms

    form_class = None
    dummy_bases = None
    dummy_attrs = None
    valid_data = None

    def get_form_class(self):
        return self.form_class

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        return form_class(**kwargs)

    def get_valid_form(self):
        form = self.get_form(data=self.valid_data.copy())
        if self.valid_data and not form.is_valid():
            error_msg = 'self.valid_data did not contain valid data! form errors: {}'.format(
                [(k, v) for k, v in form.errors.items()])
            raise Exception(error_msg)
        return form

    def get_dummy_form_class(self, bases=None, attrs=None):
        if bases is None:
            bases = self.dummy_bases or (object,)
        if attrs and self.dummy_attrs:
            class_attrs = {**self.dummy_attrs, **attrs}
        elif attrs:
            class_attrs = attrs.copy()
        elif self.dummy_attrs:
            class_attrs = self.dummy_attrs.copy()
        else:
            class_attrs = {}
        return type('DummyForm', bases, class_attrs)

    def get_dummy_form(self, bases=None, attrs=None, **form_initkwargs):
        return self.get_dummy_form_class(bases, attrs)(**form_initkwargs)

    def assertFormValid(self, form, msg=None):
        if not form.is_valid():
            form_errors = [(k, v) for k, v in form.errors.items()]
            self.fail(self._formatMessage(msg, 'Form invalid. Form errors: {}'.format(form_errors)))

    def assertFormInvalid(self, form, msg=None):
        if form.is_valid():
            self.fail(self._formatMessage(msg, 'Form valid when expected to be invalid'))


class ModelFormTestCase(DataTestCase, FormTestCase):
    fields = None

    # TODO: get_form_class should call forms.modelform_factory, and get_form
    #  should call get_form_class

    def get_form(self, **kwargs):
        return forms.modelform_factory(
            self.model, form=self.form_class, fields=self.fields)(**kwargs)
