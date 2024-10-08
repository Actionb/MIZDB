import contextlib
import re
import sys
import warnings
from urllib.parse import unquote

import pytest
from django import forms
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth import get_permission_codename, get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase
from django.urls import reverse

# Display all warnings:
if not sys.warnoptions:
    import os

    warnings.simplefilter("default")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "default"  # Also affect subprocesses


class MIZTestCase(TestCase):
    @contextlib.contextmanager
    def assertNotRaises(self, exceptions, msg=None):
        """Assert that the body does NOT raise one of the passed exceptions."""
        try:
            yield
        except exceptions as e:
            self.fail(self._formatMessage(msg, f"{e.__class__.__name__} raised."))

    def assertOrderedDictEqual(self, first, second):
        """
        Assert that the ordered dictionaries are the same by comparing the
        order of keys and the values of both dictionaries.
        """
        self.assertEqual(list(first.keys()), list(second.keys()))
        first_iter = first.items().__iter__()
        second_iter = second.items().__iter__()
        i = 0
        while True:
            try:
                first_k, first_v = next(first_iter)
                second_k, second_v = next(second_iter)
                with self.subTest(key=first_k, i=i):
                    self.assertEqual(first_k, second_k)
                    self.assertEqual(first_v, second_v)
            except StopIteration:
                break
            i += 1


@pytest.mark.django_db
class DataTestCase(MIZTestCase):
    model = None
    queryset = None

    def setUp(self):
        super().setUp()
        self.queryset = self.model.objects.all()


@pytest.mark.django_db
class UserTestCase(MIZTestCase):
    super_user = None
    staff_user = None
    noperms_user = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.super_user = get_user_model().objects.create_superuser(
            username="superuser", password="foobar", email="testtest@test.test"
        )
        cls.staff_user = get_user_model().objects.create_user(username="staff", password="foo", is_staff=True)
        cls.noperms_user = get_user_model().objects.create_user(username="noperms", password="bar")

    def setUp(self):
        super().setUp()
        # Have the super_user be logged in by default:
        self.client.force_login(self.super_user)

    def add_permission(self, user, action, model):
        codename = get_permission_codename(action, model._meta)
        ct = ContentType.objects.get_for_model(model)
        user.user_permissions.add(Permission.objects.get(codename=codename, content_type=ct))
        return self.reload_user(user)

    def reload_user(self, user):
        """Reload user from database and return it. This resets the permission cache."""
        return get_user_model().objects.get(pk=user.pk)


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

    def post_request(self, path="", data=None, user=None, **kwargs):
        """Construct a POST request using the django RequestFactory."""
        request = self.rf.post(path, data, **kwargs)
        request.user = user or self.super_user
        return request

    def get_request(self, path="", data=None, user=None, **kwargs):
        """Construct a GET request using the django RequestFactory."""
        request = self.rf.get(path, data, **kwargs)
        request.user = user or self.super_user
        return request

    def _has_message(self, expected, messages):
        if isinstance(expected, str):

            def test(m):
                return expected in m
        else:

            def test(m):
                return re.search(expected, m)

        return any(test(m) for m in messages)

    def assertMessageSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} not found in messages: {}".format(expected_message, messages)
        if not self._has_message(expected_message, messages):
            self.fail(self._formatMessage(msg, error_msg))

    def assertMessageNotSent(self, request, expected_message, msg=None):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(expected_message, messages)
        if self._has_message(expected_message, messages):
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


class AdminTestCase(DataTestCase, RequestTestCase):
    admin_site = None
    model_admin_class = None

    changelist_path = ""
    change_path = ""
    add_path = ""

    @classmethod
    def setUpTestData(cls):
        assert cls.admin_site is not None, "admin_site attribute must be set"
        super().setUpTestData()
        opts = cls.model._meta
        url_name = f"{cls.admin_site.name}:{opts.app_label}_{opts.model_name}"
        if not cls.changelist_path:
            cls.changelist_path = reverse(url_name + "_changelist")
        if not cls.change_path:
            cls.change_path = unquote(reverse(url_name + "_change", args=["{pk}"]))
        if not cls.add_path:
            cls.add_path = reverse(url_name + "_add")

    def setUp(self):
        super().setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)

    def get_changelist(self, request):
        return self.model_admin.get_changelist_instance(request)


class ModelFormTestCase(DataTestCase):
    fields = None
    form_class = None

    def get_form_class(self):
        return forms.modelform_factory(self.model, form=self.form_class, fields=self.fields)

    def get_form(self, **kwargs):
        return self.get_form_class()(**kwargs)


class LoggingTestMixin(object):
    """
    Provide TestCases with assertions that verify that a change to a model
    object has been logged.
    """

    def assertLogged(self: TestCase, objects, action_flag, change_message=None, **kwargs):
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
                "object_id": pk,
                "content_type__pk": content_type.pk,
                "action_flag": action_flag,
                "change_message": change_message,
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
                    model=ContentType.objects.get_for_id(filter_params["content_type__pk"]).model,
                )
                for values in (
                    LogEntry.objects.order_by("pk").filter(**filter_params).values("pk", *list(filter_params))
                ):
                    pk = values.pop("pk")
                    ct_model = ContentType.objects.get_for_id(values["content_type__pk"]).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(values.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by("pk").filter(**filter_params):
                    msg += "\n{}: {}".format(str(log_entry.pk), log_entry.get_change_message())
                msg += "\nCheck your test method or state of LogEntry table."
                raise AssertionError(msg)
        if unlogged:
            msg = "LogEntry for {op} missing on objects: {unlogged_objects}, " "model: ({model_name}).".format(
                op=["ADDITION", "CHANGE", "DELETION"][action_flag - 1],
                unlogged_objects=[i[0] for i in unlogged],
                model_name=model._meta.model_name,
            )

            for _obj, filter_params in unlogged:
                msg += "\nFilter parameters used: "
                msg += "\n{}; {}".format(
                    sorted(filter_params.items()),
                    ContentType.objects.get_for_id(filter_params["content_type__pk"]).model,  # noqa
                )
                msg += "\nLogEntry values: "
                for log_entry in LogEntry.objects.order_by("pk").values("pk", *list(filter_params)):
                    pk = log_entry.pop("pk")
                    ct_model = ContentType.objects.get_for_id(log_entry["content_type__pk"]).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(log_entry.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by("pk"):
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
