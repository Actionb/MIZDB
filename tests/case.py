import contextlib
import sys
import warnings
from importlib import import_module
from unittest.mock import Mock

from django import forms
from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.db.models.query import QuerySet
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path, reverse
from django.utils.http import unquote

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
    def assertSelect2JS(
            self,
            js,
            jquery='',
            select2='',
            jquery_init=''
    ):  # TODO: remove: only used once
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
        # TODO: remove this
        # Refresh each test_data instance and prepare an instance-only queryset
        # # for each instance.
        # for c, obj in enumerate(self.test_data, 1):
        #     obj.refresh_from_db()
        #     setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk))
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
            username='superuser', password='foobar', email='testtest@test.test'
        )
        cls.staff_user = User.objects.create_user(username='staff', password='foo', is_staff=True)
        cls.noperms_user = User.objects.create_user(username='noperms', password='bar')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]

    def setUp(self):
        super().setUp()
        # Have the super_user be logged in by default:
        self.client.force_login(self.super_user)


class RequestTestCase(UserTestCase):
    rf = RequestFactory()

    def get_response(self, path, data=None, user=None, **kwargs):
        """Return the response to a GET request using the django test client."""
        if user:
            self.client.force_login(user)
        return self.client.get(path, data, **kwargs)

    def post_response(self, path, data=None, user=None, **kwargs):
        """Return the response to a POST request using the django test client."""
        if user:
            self.client.force_login(user)
        return self.client.post(path, data, **kwargs)

    def post_request(self, path='', data=None, user=None, **kwargs):
        """Construct a POST request using the django RequestFactory."""
        request = self.rf.post(path, data, **kwargs)
        request.user = user or self.super_user
        return request

    def get_request(self, path='', data=None, user=None, **kwargs):
        """Construct a GET request using the django RequestFactory."""
        request = self.rf.get(path, data, **kwargs)
        request.user = user or self.super_user
        return request

    def assertMessageSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} not found in messages: {}".format(
            expected_message, [m[:len(expected_message) + 5] + "[...]" for m in messages]
        )
        if not any(m.startswith(expected_message) for m in messages):
            self.fail(self._formatMessage(msg, error_msg))

    def assertMessageNotSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(
            expected_message, [m[:len(expected_message) + 5] + "[...]" for m in messages]
        )
        if any(m.startswith(expected_message) for m in messages):
            self.fail(self._formatMessage(msg, error_msg))


class ViewTestCase(RequestTestCase):
    view_class = None

    def get_view(self, request=None, args=None, kwargs=None, **initkwargs):
        """
        Instantiate and set up the view without calling dispatch().

        initkwargs are the keyword arguments for the view_class constructor.
        args and kwargs are passed to view.setup().
        """
        view = self.view_class(**initkwargs)
        view.setup(request, *(args or ()), **(kwargs or {}))
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
    admin_site = None
    model_admin_class = None

    changelist_path = ''
    change_path = ''
    add_path = ''

    @classmethod
    def setUpTestData(cls):
        assert cls.admin_site is not None, "admin_site attribute must be set"
        super().setUpTestData()
        opts = cls.model._meta
        url_name = f"{cls.admin_site.name}:{opts.app_label}_{opts.model_name}"
        if not cls.changelist_path:
            cls.changelist_path = reverse(url_name + '_changelist')
        if not cls.change_path:
            cls.change_path = unquote(reverse(url_name + '_change', args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse(url_name + '_add')

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
                [(k, v) for k, v in form.errors.items()]
            )
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
            self.model, form=self.form_class, fields=self.fields
        )(**kwargs)


# noinspection PyPep8Naming
class LoggingTestMixin(object):
    """
    Provide TestCases with assertions that verify that a change to a model
    object has been logged.
    """

    def assertLogged(self, objects, action_flag, change_message=None, **kwargs):
        if not objects:
            return
        if not LogEntry.objects.exists():
            raise AssertionError("LogEntry table is empty!")
        unlogged = []
        if not isinstance(objects, (list, tuple, set)):
            objects = [objects]
        # Prepare the change_message:
        if not change_message:
            if action_flag == ADDITION:
                change_message = [{"added": {}}]
            elif action_flag == CHANGE:
                change_message = [{"changed": {}}]
            elif action_flag == DELETION:
                change_message = [{"deleted": {}}]
        if not isinstance(change_message, str):
            change_message = str(change_message)
        change_message = change_message.replace("'", '"')

        for obj in objects:
            pk = obj.pk
            model = obj._meta.model
            content_type = get_content_type_for_model(model)
            filter_params = {
                'object_id': pk,
                'content_type__pk': content_type.pk,
                'action_flag': action_flag,
                'change_message': change_message
            }
            filter_params.update(**kwargs)
            qs = LogEntry.objects.filter(**filter_params)
            if not qs.exists():
                unlogged.append((obj, filter_params))
                continue
            if qs.count() > 1:
                msg = (
                    "Could not verify uniqueness of LogEntry for object {object}."
                    "\nNumber of matching logs: {count}."
                    "\nFilter parameters used: "
                    "\n{items}; {model}"
                    "\nLogEntry values: "
                ).format(
                    object=obj,
                    count=qs.count(),
                    items=sorted(filter_params.items()),
                    model=ContentType.objects.get_for_id(filter_params['content_type__pk']).model,
                )
                for values in (
                        LogEntry.objects
                                .order_by('pk')
                                .filter(**filter_params)
                                .values('pk', *list(filter_params))
                ):
                    pk = values.pop('pk')
                    ct_model = ContentType.objects.get_for_id(values['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(values.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by('pk').filter(**filter_params):
                    msg += "\n{}: {}".format(str(log_entry.pk), log_entry.get_change_message())
                msg += "\nCheck your test method or state of LogEntry table."
                raise AssertionError(msg)
        if unlogged:
            # noinspection PyUnboundLocalVariable
            msg = (
                "LogEntry for {op} missing on objects: {unlogged_objects}, "
                "model: ({model_name})."
            ).format(
                op=['ADDITION', 'CHANGE', 'DELETION'][action_flag - 1],
                unlogged_objects=[i[0] for i in unlogged],
                model_name=model._meta.model_name,
            )

            for _obj, filter_params in unlogged:
                msg += "\nFilter parameters used: "
                msg += "\n{}; {}".format(
                    sorted(filter_params.items()),
                    ContentType.objects.get_for_id(filter_params['content_type__pk']).model
                )
                msg += "\nLogEntry values: "
                for log_entry in LogEntry.objects.order_by('pk').values('pk', *list(filter_params)):
                    pk = log_entry.pop('pk')
                    ct_model = ContentType.objects.get_for_id(log_entry['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(log_entry.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by('pk'):
                    msg += "\n{}: {}".format(str(log_entry.pk), log_entry.get_change_message())
            self.fail(msg)

    def assertLoggedAddition(self, obj, **kwargs):
        """Assert that a LogEntry for `obj` with action_flag == ADDITION exists."""
        self.assertLogged(obj, ADDITION, **kwargs)

    def assertLoggedChange(self, obj, **kwargs):
        """Assert that a LogEntry for `obj` with action_flag == CHANGE exists."""
        self.assertLogged(obj, CHANGE, **kwargs)

    def assertLoggedDeletion(self, objects, **kwargs):
        """Assert that a LogEntry for `obj` with action_flag == DELETION exists."""
        self.assertLogged(objects, DELETION, **kwargs)
