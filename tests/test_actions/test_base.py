from unittest.mock import DEFAULT, Mock, patch

from django import forms
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.http import HttpResponse
from django.test import override_settings
from django.urls import path, reverse
from django.views import View
from django.views.generic.base import ContextMixin
from formtools.wizard.views import SessionWizardView

from dbentry.actions.base import (
    ActionConfirmationView,
    ActionMixin,
    AdminActionConfirmationView,
    AdminActionMixin,
    WizardConfirmationView,
    get_object_link,
)
from dbentry.admin.forms import MIZAdminForm
from dbentry.site.views.base import ACTION_SELECTED_ITEM
from tests.case import AdminTestCase, DataTestCase, RequestTestCase
from tests.model_factory import make
from tests.test_actions.case import ActionViewTestCase, AdminActionViewTestCase
from tests.test_actions.models import Band

admin_site = admin.AdminSite(name="test_actions")


class RenameConfirmationForm(MIZAdminForm):
    new_name = forms.CharField()


class RenameBandActionView(AdminActionConfirmationView):
    """Dummy action view class."""

    title = "Rename Band"
    breadcrumbs_title = "Rename"
    action_name = "rename_band"
    action_allowed_checks = ("bands_are_active",)  # Require that only active bands can be renamed
    form_class = RenameConfirmationForm
    admin_site = admin_site

    def bands_are_active(view):  # noqa
        """Return whether all selected Band objects are active."""
        return not view.queryset.exclude(status=Band.Status.ACTIVE).exists()

    def form_valid(self, form) -> None:
        """Rename all Band objects in the view's queryset."""
        self.queryset.update(band_name=form.cleaned_data["new_name"])
        return None


def rename_band(model_admin, request, queryset):
    """Dummy action view FUNCTION."""
    return RenameBandActionView.as_view(model_admin=model_admin, queryset=queryset)(request)


rename_band.short_description = "Rename all Band objects for fun and profit!"
rename_band.allowed_permissions = ("change",)  # Require that the user has change permission


@admin.register(Band, site=admin_site)
class BandAdmin(admin.ModelAdmin):
    actions = [rename_band]

    @property
    def media(self):
        return forms.Media(js=("admin/admin.js",))


def dummy_view(*_args, **_kwargs):
    return HttpResponse("test")


class URLConf:
    urlpatterns = [
        path("test_actions/", admin_site.urls),
        path("band/<path:object_id>/change", dummy_view, name="test_actions_band_change"),
        path("genre/<path:object_id>/change", dummy_view, name="test_actions_genre_change"),
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestGetObjectLink(DataTestCase, RequestTestCase):
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.obj = obj = make(cls.model, band_name="Khruangbin")
        opts = obj._meta
        cls.change_url = reverse(f"{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
        super().setUpTestData()

    def test_get_object_link(self):
        """
        Assert that get_object_link returns the expected string:
        '<model.verbose_name>: <url>'.
        """
        self.assertEqual(
            get_object_link(self.get_request(), self.obj, ""),
            f'Band: <a href="{self.change_url}" target="_blank">Khruangbin</a>',
        )

    def test_get_object_link_no_change_page_URL(self):
        """
        Assert that get_object_link returns '<model.verbose_name>: <str(obj)>'
        if no URL to the change page could be found.
        """
        self.assertEqual(get_object_link(self.get_request(user=self.noperms_user), self.obj, ""), "Band: Khruangbin")


def function_check(_view):
    """
    A function for the action_allowed_checks of 'DummyView' to assert that
    get_action_allowed_checks() includes functions that do not belong to the
    action view class.
    """
    return True


@override_settings(ROOT_URLCONF=URLConf)
class TestActionMixin(ActionViewTestCase):
    class DummyView(ActionMixin, ContextMixin, View):
        action_allowed_checks = ["not_callable", "check_true", function_check]
        not_callable = ()

        def check_true(view):  # noqa
            """A function for the action_allowed_checks that returns True."""
            return True

        def check_false(view):  # noqa
            """A function for the action_allowed_checks that returns False."""
            return False

    model = Band
    view_class = DummyView

    def test_init_sets_action_name(self):
        """
        init should set the 'action_name' attribute to the view class name, if
        the class attribute is not set.
        """
        queryset = self.model.objects.all()
        view = self.view_class(queryset=queryset)
        self.assertEqual(view.action_name, "DummyView")

        with patch.object(self.view_class, "action_name", new="test"):
            view = self.view_class(queryset=queryset)
            self.assertEqual(view.action_name, "test")

    def test_get_action_allowed_checks(self):
        """
        Assert that get_action_allowed_checks only yields unbound class methods
        or function callables.
        """
        view = self.get_view()
        self.assertEqual([self.view_class.check_true, function_check], list(view.get_action_allowed_checks()))

    def test_action_allowed_no_checks_false(self):
        """Assert that action_allowed returns True, if no check returns False."""
        view = self.get_view()
        self.assertTrue(view.action_allowed())

    def test_action_allowed_check_returns_false(self):
        """Assert that action_allowed returns False, if a check return False."""
        view = self.get_view()
        checks = view.action_allowed_checks + [self.view_class.check_false]
        with patch.object(view, "action_allowed_checks", new=checks):
            self.assertFalse(view.action_allowed())

    def test_dispatch_action_not_allowed(self):
        """Assert that dispatch returns None, if the action is not allowed."""
        view = self.get_view()
        with patch.object(view, "action_allowed", new=Mock(return_value=False)):
            self.assertIsNone(view.dispatch(self.get_request()))

    def test_get_context_data_contains_titel(self):
        """Assert that the context data includes a 'titel' item."""
        view = self.get_view(self.get_request())
        view.title = "Merge %(verbose_name_plural)s"
        context = view.get_context_data()
        self.assertEqual(context["title"], "Merge Bands")

    def test_get_context_data_object_name_singular(self):
        """
        Assert that the context_data 'objects_name' is the singular
        verbose_name when the queryset contains exactly one object.
        """
        view = self.get_view(self.get_request())
        view.queryset = Mock(count=Mock(return_value=1))
        context = view.get_context_data()
        self.assertEqual(context["objects_name"], "Band")

    def test_get_context_data_object_name_plural(self):
        """
        Assert that the context_data 'objects_name' is verbose_name_plural when
        the queryset contains zero or multiple objects.
        """
        view = self.get_view(self.get_request())
        for count in (0, 2):
            with self.subTest(number=count):
                view.queryset = Mock(count=Mock(return_value=count))
                context = view.get_context_data()
                self.assertEqual(context["objects_name"], "Bands")

    def test_get_context_data_adds_action_selection_name(self):
        view = self.get_view(self.post_request(), model=self.model)
        context_data = view.get_context_data()
        self.assertIn("action_selection_name", context_data)
        self.assertEqual(context_data["action_selection_name"], ACTION_SELECTED_ITEM)


@override_settings(ROOT_URLCONF=URLConf)
class TestAdminActionMixin(AdminActionViewTestCase):
    class AdminActionView(AdminActionMixin, ActionMixin, ContextMixin, View):
        pass

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin
    view_class = AdminActionView

    def test_init_sets_url_namespace(self):
        """
        Assert that the value for attribute 'url_namespace' is set to the site
        name of the model admin's admin_site.
        """
        view = self.get_view(self.get_request())
        self.assertEqual(view.url_namespace, admin_site.name)

    def test_get_context_data(self):
        """Assert that the context data includes items for 'breadcrumbs_title'."""
        view = self.get_view(self.get_request())
        view.breadcrumbs_title = "Merging one %(verbose_name)s and another %(verbose_name)s"

        self.assertEqual(view.get_context_data()["breadcrumbs_title"], "Merging one Band and another Band")

    def test_get_context_data_model_admin_media(self):
        """Assert that the media from the model admin is added."""
        view = self.get_view(self.get_request(), model_admin=self.model_admin)
        context = view.get_context_data()
        self.assertEqual(str(context["media"]), str(self.model_admin.media))

    def test_get_context_data_adds_media_from_kwargs(self):
        """Assert that the media from get_context_data kwargs is added."""
        view = self.get_view(self.get_request(), model_admin=self.model_admin)
        media = forms.Media(js=("admin/test.js",))
        context = view.get_context_data(media=media)
        self.assertEqual(str(context["media"]), str(media + self.model_admin.media))

    def test_get_context_data_adds_media_from_form(self):
        """Assert that the media from the action view's form is added."""
        form_media = forms.Media(js=("admin/form.js",))

        class Form(forms.Form):
            @property
            def media(self):
                return form_media

        view = self.get_view(self.get_request(), model_admin=self.model_admin)
        with patch.object(view, "get_form", create=True) as get_form_mock:
            get_form_mock.return_value = Form()
            context = view.get_context_data()
            self.assertEqual(str(context["media"]), str(self.model_admin.media + form_media))

    def test_get_context_data_adds_action_selection_name(self):
        view = self.get_view(self.post_request(), model=self.model)
        context_data = view.get_context_data()
        self.assertIn("action_selection_name", context_data)
        self.assertEqual(context_data["action_selection_name"], ACTION_CHECKBOX_NAME)


@override_settings(ROOT_URLCONF=URLConf)
class TestActionConfirmationView(ActionViewTestCase):
    class DummyView(ActionConfirmationView):
        form_class = type("DummyForm", (forms.Form,), {})  # ActionConfirmationView is a FormView

    model = Band
    view_class = DummyView

    @patch("dbentry.actions.base.super")
    def test_get_form_kwargs(self, super_mock):
        """
        Assert that the kwargs returned by get_form_kwargs only includes 'data'
        if the action was confirmed.
        """
        super_mock.return_value.get_form_kwargs = Mock(return_value={"data": ""})
        view = self.get_view(request=self.post_request(), model=self.model)
        with patch.object(view, "action_confirmed") as action_confirmed_mock:
            for action_confirmed in (True, False):
                action_confirmed_mock.return_value = action_confirmed
                with self.subTest(action_confirmed=action_confirmed):
                    form_kwargs = view.get_form_kwargs()
                    if action_confirmed:
                        self.assertIn("data", form_kwargs)
                    else:
                        self.assertNotIn("data", form_kwargs)

    def test_action_confirmed_true(self):
        request = self.post_request(data={self.view_class.action_confirmed_name: ""})
        view = self.get_view(request, model=self.model)
        self.assertTrue(view.action_confirmed(request))

    def test_action_confirmed_false(self):
        request = self.post_request(data={})
        view = self.get_view(request, model=self.model)
        self.assertFalse(view.action_confirmed(request))


@override_settings(ROOT_URLCONF=URLConf)
class TestWizardConfirmationView(ActionViewTestCase):
    view_class = WizardConfirmationView
    model = Band

    def test_post_first_visit(self):
        """
        If the 'current_step' is missing from the request POST data, post()
        should prepare the storage engine and render the first form.
        """
        view = self.get_view()
        request = self.post_request()
        with patch.multiple(
            view,
            storage=DEFAULT,
            steps=Mock(first="first step"),
            get_form=DEFAULT,
            render=Mock(return_value="Rendered form."),
            create=True,
        ):
            self.assertEqual(view.post(request), "Rendered form.")
            self.assertEqual(view.storage.reset.call_count, 1)
            self.assertEqual(view.storage.current_step, "first step")

    def test_post_step_data(self):
        """
        If the request contains data about the current step, post should call
        the super method.
        """
        view = self.get_view()
        # The key for the current step consists of a 'normalized' version of
        # the view class name plus '-current_step':
        normalized_name = "wizard_confirmation_view"
        request = self.post_request(data={normalized_name + "-current_step": "2"})
        with patch.object(SessionWizardView, "post", return_value="WizardForm!"):
            self.assertEqual(view.post(request), "WizardForm!")


@override_settings(ROOT_URLCONF=URLConf)
class TestConfirmationViewsIntegrated(AdminTestCase):
    """Integration test for ActionConfirmationView and ActionMixin."""

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)
        cls.inactive = make(cls.model, status=Band.Status.INACTIVE)
        super().setUpTestData()

    def test_rename(self):
        """
        Assert that the confirmation form is displayed before proceeding with
        the action.
        """
        request_data = {"action": "rename_band", helpers.ACTION_CHECKBOX_NAME: [str(self.obj.pk)]}  # selected objects
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/action_confirmation.html")

        # Add form data and confirm the action:
        request_data["new_name"] = "RENAMED"
        request_data["action_confirmed"] = "1"
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Should have been returned to the changelist:
        self.assertTemplateUsed(response, "admin/change_list.html")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.band_name, "RENAMED")

    def test_action_not_allowed(self):
        """
        The user should be redirected back to the changelist, if the action is
        not allowed.
        """
        request_data = {
            "action": "rename_band",
            helpers.ACTION_CHECKBOX_NAME: [str(self.inactive.pk)],  # selected objects
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/change_list.html")
