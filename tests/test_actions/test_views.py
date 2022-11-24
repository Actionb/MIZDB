from unittest.mock import DEFAULT, Mock, PropertyMock, patch

from django import forms
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms.formsets import ManagementForm
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import override as translation_override
from django.views.generic.base import ContextMixin, View
from formtools.wizard.views import SessionWizardView, WizardView

import dbentry.admin as _admin
import dbentry.models as _models
from dbentry.actions import actions as _actions
from dbentry.actions.base import (
    ActionConfirmationView, ConfirmationViewMixin, WizardConfirmationView, get_object_link
)
from dbentry.actions.forms import (
    BrochureActionFormOptions, BrochureActionFormSet, MergeConflictsFormSet, MergeFormSelectPrimary
)
from dbentry.actions.views import (
    BulkEditJahrgang, ChangeBestand, MergeView, MoveToBrochure, Replace
)
from dbentry.base.forms import MIZAdminForm
from dbentry.base.views import MIZAdminMixin
from dbentry.sites import miz_site
from dbentry.utils import get_obj_link
from tests.case import AdminTestCase, LoggingTestMixin, ViewTestCase
from tests.factory import make
from .models import Audio, Band, Genre

admin_site = admin.AdminSite(name='test_actions')


class RenameConfirmationForm(MIZAdminForm):
    new_name = forms.CharField()


class RenameBandActionView(ActionConfirmationView):
    """Dummy action view class."""

    title = 'Rename Band'
    breadcrumbs_title = 'Rename'
    short_description = 'Rename all Band objects for fun and profit!'
    action_name = 'rename_band'
    allowed_permissions = ('change',)  # Require that the user has change permission
    action_allowed_checks = ('bands_are_active',)  # Require that only active bands can be renamed
    form_class = RenameConfirmationForm
    admin_site = admin_site

    def bands_are_active(view):  # noqa
        """Return whether all selected Band objects are active."""
        return not view.queryset.exclude(status=Band.Status.ACTIVE).exists()

    def perform_action(self, cleaned_data) -> None:
        """Rename all Band objects in the view's queryset."""
        self.queryset.update(band_name=cleaned_data['new_name'])


def rename_band(model_admin, request, queryset):
    """Dummy action view FUNCTION."""
    return RenameBandActionView.as_view(model_admin=model_admin, queryset=queryset)(request)


rename_band.short_description = RenameBandActionView.short_description  # noqa
rename_band.allowed_permissions = RenameBandActionView.allowed_permissions


@admin.register(Band, site=admin_site)
class BandAdmin(admin.ModelAdmin):
    actions = [rename_band]

    @property
    def media(self):
        return forms.Media(js=('admin/admin.js',))


@admin.register(Genre, site=admin_site)
class GenreAdmin(admin.ModelAdmin):
    actions = [_actions.replace]

    def has_superuser_permission(self, request):
        return request.user.is_superuser


@admin.register(Audio, site=admin_site)
class AudioAdmin(admin.ModelAdmin):
    pass


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestGetObjectLink(AdminTestCase):
    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, band_name='Khruangbin')
        super().setUpTestData()

    def test_get_object_link(self):
        """
        Assert that get_object_link returns the expected string:
        '<model.verbose_name>: <url>'.
        """
        url = self.change_path.format(pk=self.obj.pk)
        self.assertEqual(
            get_object_link(self.obj, self.super_user, self.admin_site.name),
            f'Band: <a href="{url}" target="_blank">Khruangbin</a>'
        )

    def test_get_object_link_no_change_page_URL(self):
        """
        Assert that get_object_link returns '<model.verbose_name>: <str(obj)>'
        if no URL to the change page could be found.
        """
        self.assertEqual(
            get_object_link(self.obj, self.noperms_user, self.admin_site.name),
            'Band: Khruangbin'
        )


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestConfirmations(AdminTestCase):
    """Integration test for ActionConfirmationView (and ConfirmationViewMixin)."""

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)
        cls.inactive = make(cls.model, status=Band.Status.INACTIVE)
        super().setUpTestData()

    def test_rename(self):
        """Assert that the confirmation form is displayed before proceeding with the action."""
        request_data = {
            'action': 'rename_band',
            helpers.ACTION_CHECKBOX_NAME: [str(self.obj.pk)]  # selected objects
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/action_confirmation.html')

        # Add form data and confirm the action:
        request_data['new_name'] = 'RENAMED'
        request_data['action_confirmed'] = '1'
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Should have been returned to the changelist:
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.band_name, 'RENAMED')

    def test_action_not_allowed(self):
        """The user should be redirected back to the changelist, if the action is not allowed."""
        request_data = {
            'action': 'rename_band',
            helpers.ACTION_CHECKBOX_NAME: [str(self.inactive.pk)]  # selected objects
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')


class ActionViewTestCase(AdminTestCase, ViewTestCase):
    action_name = ''

    def get_view(self, request=None, args=None, kwargs=None, action_name=None, **initkwargs):
        initkwargs = {
            'model_admin': self.model_admin, 'queryset': self.queryset.all(),
            'action_name': action_name or self.action_name, **initkwargs
        }
        return super().get_view(request=request, args=args, kwargs=kwargs, **initkwargs)


def outside_check(view):
    """A function for the action_allowed_checks of 'DummyView'."""
    return True


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestConfirmationViewMixin(ActionViewTestCase):
    class DummyView(ConfirmationViewMixin, ContextMixin, View):
        admin_site = admin_site
        action_allowed_checks = ['not_callable', 'check_true', outside_check]
        not_callable = ()

        def check_true(view):  # noqa
            """A function for the action_allowed_checks"""
            return True

        def check_false(view):  # noqa
            """A function for the action_allowed_checks"""
            return False

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin
    view_class = DummyView

    def test_init_sets_action_name(self):
        """
        init should set the 'action_name' attribute to the view class name, if
        the class attribute is not set.
        """
        queryset = self.model.objects.all()
        view = self.view_class(model_admin=self.model_admin, queryset=queryset)
        self.assertEqual(view.action_name, 'DummyView')

        with patch.object(self.view_class, 'action_name', new='test'):
            view = self.view_class(model_admin=self.model_admin, queryset=queryset)
            self.assertEqual(view.action_name, 'test')

    def test_get_action_allowed_checks(self):
        """get_action_allowed_checks should yield unbound methods or function callables."""
        view = self.get_view()
        self.assertEqual(
            [self.view_class.check_true, outside_check],
            list(view.get_action_allowed_checks())
        )

    def test_action_allowed(self):
        """
        Assert that action_allowed returns False, if a check return False, and
        returns True if no checks return False.
        """
        view = self.get_view()
        self.assertTrue(view.action_allowed)
        view = self.get_view()
        checks = view.action_allowed_checks + [self.view_class.check_false]
        with patch.object(view, 'action_allowed_checks', new=checks):
            self.assertFalse(view.action_allowed)

    def test_dispatch_action_not_allowed(self):
        """
        dispatch should redirect back to the changelist (return None), if the
        action is not allowed.
        """
        view = self.get_view()
        view._action_allowed = False
        self.assertIsNone(view.dispatch(self.get_request()))
        view._action_allowed = True
        self.assertIsNotNone(view.dispatch(self.get_request()))

    def test_get_context_data(self):
        """
        Assert that the context data includes items for 'titel',
        'breadcrumbs_title' and 'non_reversible_warning'.
        """
        view = self.get_view(self.get_request())
        view.title = 'Merge %(verbose_name_plural)s'
        view.breadcrumbs_title = 'Merging one %(verbose_name)s and another %(verbose_name)s'
        view.non_reversible_warning = 'This action cannot be reversed.'

        context = view.get_context_data()
        self.assertEqual(context['title'], 'Merge Bands')
        self.assertEqual(context['breadcrumbs_title'], 'Merging one Band and another Band')
        self.assertEqual(context['non_reversible_warning'], 'This action cannot be reversed.')

    def test_get_context_data_adds_media(self):
        """Assert that the media of the model admin and the form are added."""
        # No form:
        view = self.get_view(self.get_request())
        context = view.get_context_data()
        self.assertEqual(str(context['media']), str(self.model_admin.media))

        # Inject custom media:
        media = forms.Media(js=('admin/test.js',))
        context = view.get_context_data(media=media)
        self.assertEqual(str(context['media']), str(media + self.model_admin.media))

        # Form with media:
        form_media = forms.Media(js=('admin/form.js',))

        class Form(forms.Form):
            @property
            def media(self):
                return form_media

        view.get_form = Mock(return_value=Form())

        context = view.get_context_data()
        self.assertEqual(str(context['media']), str(self.model_admin.media + form_media))

        context = view.get_context_data(media=media)
        self.assertEqual(str(context['media']), str(media + self.model_admin.media + form_media))

    def test_get_context_data_object_name_singular(self):
        """
        Assert that the context_data 'objects_name' is the singular
        verbose_name when the queryset contains exactly one object.
        """
        view = self.get_view(self.get_request())
        view.queryset = Mock(count=Mock(return_value=1))
        context = view.get_context_data()
        self.assertEqual(context['objects_name'], 'Band')

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
                self.assertEqual(context['objects_name'], 'Bands')


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestActionConfirmationView(ActionViewTestCase):
    class DummyView(ActionConfirmationView):
        admin_site = admin_site
        form_class = type('DummyForm', (forms.Form,), {})  # ActionConfirmationView is a FormView

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin
    view_class = DummyView

    @classmethod
    def setUpTestData(cls):
        cls.genres = genres = [make(Genre, genre='Funk'), make(Genre, genre='Soul')]
        cls.obj = make(cls.model, band_name='Khruangbin', genres=genres, status=Band.Status.ACTIVE)

        super().setUpTestData()

    def test_get_form_kwargs_data_item(self):
        """
        Assert that the 'data' kwarg is removed, unless the request contains an
        'action_confirmed' item.
        """
        view = self.get_view(self.post_request('/'))
        self.assertNotIn('data', view.get_form_kwargs())
        self.assertNotIn('files', view.get_form_kwargs())
        view = self.get_view(self.post_request('/', data={'action_confirmed': '1'}))
        self.assertIn('data', view.get_form_kwargs())
        self.assertIn('files', view.get_form_kwargs())

    def test_get_objects_list(self):
        view = self.get_view(
            self.get_request(),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),
            display_fields=['band_name', 'genres', 'status']
        )
        user = view.request.user
        link_list = view.get_objects_list()

        # link_list should have a structure like this:
        # [
        #       ('Band: <link of obj1>', [<additional info (display_fields)>]),
        #       ('Band: <link of obj2>', [<additional info (display_fields)>]),
        #       ...
        # ]

        self.assertEqual(len(link_list), 1)
        url = self.change_path.format(pk=self.obj.pk)
        self.assertEqual(link_list[0][0], f'Band: <a href="{url}" target="_blank">{self.obj}</a>')

        # link_list[0][1] is the list of values for the display fields:
        display_field_values = link_list[0][1]
        # 4 items: one for the band name, two for the genres, and one for the
        # status:
        self.assertEqual(len(display_field_values), 4)
        # 'band_name' value:
        self.assertEqual(display_field_values[0], 'Bandname: ' + self.obj.band_name)
        # links to the genres:
        genres = Genre.objects.all().order_by('genre')
        url_name = f"{self.admin_site.name}:{Genre._meta.app_label}_{Genre._meta.model_name}_change"
        url = reverse(url_name, args=[genres[0].pk])
        self.assertEqual(
            display_field_values[1], f'Genre: <a href="{url}" target="_blank">{genres[0]}</a>'
        )
        url = reverse(url_name, args=[genres[1].pk])
        self.assertEqual(
            display_field_values[2], f'Genre: <a href="{url}" target="_blank">{genres[1]}</a>'
        )
        # 'status' value:
        self.assertEqual(link_list[0][1][3], 'Status: Aktiv')

    def test_get_objects_list_no_display_fields(self):
        view = self.get_view(
            self.get_request(),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),
            display_fields=[]
        )
        url = self.change_path.format(pk=self.obj.pk)
        self.assertEqual(
            view.get_objects_list(),
            [(f'Band: <a href="{url}" target="_blank">{self.obj}</a>',)]
        )

    def test_get_objects_list_no_link(self):
        """
        Assert that a string representation of the object is presented, if
        no link could be created for it.
        """
        view = self.get_view(
            self.get_request(user=self.noperms_user),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),  # noqa
            display_fields=[]
        )
        self.assertEqual(view.get_objects_list(), [(f'Band: {self.obj}',)])

    def test_form_valid(self):
        """
        Assert that form_valid returns None to redirect the user back to the
        changelist.
        """
        view = self.get_view()
        view.perform_action = Mock()
        self.assertIsNone(view.form_valid(Mock()))

    def test_get_context_data_adds_objects_list(self):
        """Assert that 'object_list' are added to the context data."""
        view = self.get_view(self.get_request())
        with patch.object(view, 'get_objects_list'):
            self.assertIn('object_list', view.get_context_data())


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestWizardConfirmationView(ActionViewTestCase):
    admin_site = admin_site
    view_class = WizardConfirmationView
    model = Band
    model_admin_class = BandAdmin

    def test_post_first_visit(self):
        """
        If there is no 'step' data in request.POST, post() should prepare the
        storage engine and render the first form.
        """
        view = self.get_view()
        request = self.post_request()
        with patch.multiple(
                view, storage=DEFAULT, steps=Mock(first='first step'), get_form=DEFAULT,
                render=Mock(return_value='Rendered form.'), create=True
        ):
            self.assertEqual(view.post(request), 'Rendered form.')
            self.assertEqual(view.storage.reset.call_count, 1)
            self.assertEqual(view.storage.current_step, 'first step')

    def test_post_step_data(self):
        """
        If the request contains data about the current step, post should call
        the super method.
        """
        view = self.get_view()
        # The key for the current step consists of a 'normalized' version of
        # the view class name plus '-current_step':
        normalized_name = 'wizard_confirmation_view'
        request = self.post_request(data={normalized_name + '-current_step': '2'})
        with patch.object(SessionWizardView, 'post', return_value='WizardForm!'):
            self.assertEqual(view.post(request), 'WizardForm!')

    def test_done_returns_none(self):
        """
        Assert that done() returns None even if perform_action returns a value
        or if an exception occurred.
        """
        view = self.get_view()
        # 'implement' perform_action:
        with patch.object(view, 'perform_action') as perform_action_mock:
            perform_action_mock.return_value = 'Not None'
            self.assertIsNone(view.done())
            perform_action_mock.side_effect = TypeError
            with self.assertNotRaises(NotImplementedError):
                self.assertIsNone(view.done())


class TestBulkEditJahrgang(ActionViewTestCase, LoggingTestMixin):
    admin_site = miz_site
    view_class = BulkEditJahrgang
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        mag = make(_models.Magazin, magazin_name='Testmagazin')
        # obj1 should be in the initial jahrgang (i.e. jg + 0) starting in year 2000:
        cls.obj1 = make(
            cls.model, magazin=mag, ausgabejahr__jahr=[2000, 2001], e_datum='2000-06-12',
            ausgabemonat__monat__ordinal=[6]
        )
        # obj2 should be in the next jahrgang because it's one year later: jg + 1
        cls.obj2 = make(
            cls.model, magazin=mag, ausgabejahr__jahr=[2001], e_datum='2001-06-12',
            ausgabemonat__monat__ordinal=[6]
        )
        cls.other = make(cls.model, magazin=make(_models.Magazin, magazin_name='Other'))
        super().setUpTestData()

    def test(self):
        """Request updating the jahrgang values of Ausgabe instances."""
        # Request the initial form where you set the jahrgang value:
        request_data = {
            'action': 'bulk_jg',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        user = self.super_user
        response = self.post_response(
            self.changelist_path, data=request_data, user=user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/action_confirmation.html')

        # Check the contents of the 'object_list' context item.
        # It should be a list of 2-tuples. The first item of that tuple should
        # be a link to the Ausgabe instance. The second item should be the
        # values of the affected fields. The display_fields for this view are
        # 'jahrgang' and 'ausgabejahr__jahr'.
        self.assertIn('object_list', response.context)
        self.assertEqual(len(response.context['object_list']), 2)
        (obj1_link, obj1_values), (obj2_link, obj2_values) = response.context['object_list']
        link = get_obj_link(self.obj1, user, miz_site.name, blank=True)
        self.assertEqual(obj1_link, f"Ausgabe: {link}")
        self.assertEqual(obj1_values, ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"])
        link = get_obj_link(self.obj2, user, miz_site.name, blank=True)
        self.assertEqual(obj2_link, f"Ausgabe: {link}")
        self.assertEqual(obj2_values, ["Jahrgang: ---", "Jahr: 2001"])

        # Confirm and proceed with the jahrgang update
        request_data['jahrgang'] = '1'
        request_data['start'] = self.obj1.pk
        request_data['action_confirmed'] = '1'
        response = self.post_response(
            self.changelist_path, data=request_data, user=user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        # Check updated values and assert that log entry objects were added
        self.obj1.refresh_from_db()
        self.assertEqual(self.obj1.jahrgang, 1)
        self.obj2.refresh_from_db()
        self.assertEqual(self.obj2.jahrgang, 2)
        self.assertLoggedChange(self.obj1, change_message=[{"changed": {'fields': ['Jahrgang']}}])
        self.assertLoggedChange(self.obj2, change_message=[{"changed": {'fields': ['Jahrgang']}}])

    def test_jahrgang_zero(self):
        """
        Choosing 0 as the desired value for jahrgang should set the jahrgang
        for the selected objects to None.
        """
        self.obj1.jahrgang = 1
        self.obj1.save()
        self.obj2.jahrgang = 2
        self.obj2.save()
        request_data = {
            'action': 'bulk_jg',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk],
            'jahrgang': '0',
            'start': self.obj1.pk,
            'action_confirmed': '1'
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.obj1.refresh_from_db()
        self.assertIsNone(self.obj1.jahrgang)
        self.obj2.refresh_from_db()
        self.assertIsNone(self.obj2.jahrgang)

    def test_not_same_magazin(self):
        """
        The action should be aborted, if the selected objects are not related
        to the same Magazin object.
        """
        request_data = {
            'action': 'bulk_jg',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.other.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertMessageSent(
            response.wsgi_request,
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        )

    @translation_override(language=None)
    def test_permissions_required(self):
        """Assert that specific permissions are required to access this action."""
        # User needs view permission to have access to the change list. User
        # also needs access to at least one action for the action form to be
        # included (here: delete selected action).
        opts = self.model._meta
        ct = ContentType.objects.get_for_model(self.model)
        view_perm = Permission.objects.get(
            codename=get_permission_codename('view', opts), content_type=ct
        )
        delete_perm = Permission.objects.get(
            codename=get_permission_codename('delete', opts), content_type=ct
        )
        self.staff_user.user_permissions.set([view_perm, delete_perm])

        # The action should not be an option in the action form - a request
        # with that action should send us back to the change list with a
        # 'No action selected.' admin message.
        request_data = {
            'action': 'bulk_jg',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertMessageSent(response.wsgi_request, 'No action selected.')

        # Give the user the permissions required for the action:
        change_perm = Permission.objects.get(
            codename=get_permission_codename('change', opts), content_type=ct
        )
        self.staff_user.user_permissions.add(change_perm)
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/action_confirmation.html')

    def test_get_context_data_contains_helptext(self):
        """Assert that the help text(s) are included in the context data."""
        view = self.get_view(self.get_request())
        self.assertIn('view_helptext', view.get_context_data().keys())


class TestMergeViewAusgabe(ActionViewTestCase):
    admin_site = miz_site
    view_class = MergeView
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj1 = make(cls.model, magazin=mag, ausgabejahr__jahr=[2000])
        cls.obj2 = make(cls.model, magazin=mag, ausgabejahr__jahr=[2001], jahrgang=1)
        cls.obj3 = make(cls.model, ausgabejahr__jahr=[2001], jahrgang=20)
        cls.obj4 = make(cls.model, magazin=mag, jahrgang=2)
        super().setUpTestData()

    def test_action_allowed(self):
        queryset = self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view = self.get_view(queryset=queryset)
        self.assertTrue(view.action_allowed)

    @patch.object(WizardView, 'get_form_prefix')
    def test_has_merge_conflicts(self, get_prefix_mock):
        get_prefix_mock.return_value = '0'
        view = self.get_view(
            queryset=self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk])
        )
        with patch('dbentry.actions.views.get_updatable_fields') as get_fields_mock:
            get_fields_mock.return_value = ['jahrgang']
            # The values are initially collected in a set. That set is then
            # turned into a list (for serialization) - the order of the items
            # in that list
            has_conflict, updates = view._has_merge_conflicts(data={'0-primary': self.obj1.pk})
            self.assertTrue(has_conflict)
            self.assertEqual(sorted(updates['jahrgang']), ['1', '2'])

    @patch.object(WizardView, 'get_form_prefix')
    def test_has_merge_conflicts_no_primary_object(self, get_prefix_mock):
        """
        Assert that _has_merge_conflicts returns early, if the primary object
        could not be resolved.
        """
        get_prefix_mock.return_value = '0'
        view = self.get_view()
        # No primary key data for the primary object:
        self.assertEqual(view._has_merge_conflicts(data={}), (False, None))
        # No model object with that primary key:
        self.assertEqual(view._has_merge_conflicts(data={'0-primary': 0}), (False, None))

    @patch.object(WizardView, 'get_form_prefix')
    def test_has_merge_conflicts_no_updatable_fields(self, get_prefix_mock):
        """
        Assert that _has_merge_conflicts returns early, if the primary object
        has no fields that can be updated.
        """
        get_prefix_mock.return_value = '0'
        view = self.get_view()
        with patch('dbentry.actions.views.get_updatable_fields', new=Mock(return_value=[])):
            self.assertEqual(
                view._has_merge_conflicts(data={'0-primary': self.obj1.pk}),
                (False, None)
            )

    def test_process_step_adds_update_data(self):
        """Assert that process_step adds data needed for the updates."""
        # obj1 can be updated on the field 'jahrgang' with obj2's value.
        view = self.get_view(
            queryset=self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        )
        view.steps = Mock(
            current=MergeView.SELECT_PRIMARY_STEP,
            last=MergeView.CONFLICT_RESOLUTION_STEP
        )
        view.storage = Mock(current_step=MergeView.SELECT_PRIMARY_STEP)
        form = MergeFormSelectPrimary()
        form.cleaned_data = {'expand_primary': True}
        with patch.object(view, '_has_merge_conflicts') as has_conflict_mock:
            has_conflict_mock.return_value = (False, {'jahrgang': ['1']})
            data = view.process_step(form)
            self.assertIn('updates', data)
            self.assertEqual(data['updates'], {'jahrgang': ['1']})

    def test_process_step_conflict_step(self):
        """
        If the current step is the conflict resolution step, no special
        processing is needed and the data should simply be returned.
        """
        view = self.get_view()
        view.steps = Mock(current=MergeView.CONFLICT_RESOLUTION_STEP)
        with patch.object(WizardView, 'process_step', new=Mock(return_value={'foo': 'bar'})):
            self.assertEqual(view.process_step(None), {'foo': 'bar'})

    def test_process_step_no_expand(self):
        """
        If expand_primary is False, there can be no conflicts, and process_step
        should set the current step to the last step to skip the conflict
        resolution step.
        """
        view = self.get_view()
        view.steps = Mock(
            current=MergeView.SELECT_PRIMARY_STEP,
            last=MergeView.CONFLICT_RESOLUTION_STEP
        )
        view.storage = Mock(current_step=MergeView.SELECT_PRIMARY_STEP)
        form = MergeFormSelectPrimary()
        form.cleaned_data = {'expand_primary': False}
        data = view.process_step(form)
        self.assertFalse(data)
        self.assertEqual(view.storage.current_step, MergeView.CONFLICT_RESOLUTION_STEP)

    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data')
    def test_get_context_data_select_primary_step(self, super_mock):
        """
        Assert that get_context_data adds various items for the select primary
        step template.
        """
        view = self.get_view()
        step = view.SELECT_PRIMARY_STEP
        view.steps = Mock(current=step)
        super_mock.return_value = {'form': MergeFormSelectPrimary()}
        changelist_mock = Mock()
        with patch.object(view.model_admin, 'get_changelist_instance') as get_changelist_mock:
            get_changelist_mock.return_value = changelist_mock
            context = view.get_context_data()
            self.assertEqual(context['title'], 'Merge objects: step 1')
            self.assertEqual(context['cl'], changelist_mock)
            label_element = '<label class="required" for="id_primary" style="width: 100%;">'
            self.assertTrue(context['primary_label'].startswith(label_element))
            self.assertEqual(context['current_step'], '0')
            self.assertEqual(context['view_helptext'], view.view_helptext[step])

    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data')
    def test_get_context_data_select_conflict_resolution_step(self, super_mock):
        view = self.get_view()
        step = view.CONFLICT_RESOLUTION_STEP
        view.steps = Mock(current=step)
        super_mock.return_value = {}
        context = view.get_context_data()
        self.assertEqual(context['title'], 'Merge objects: step 2')
        self.assertEqual(context['view_helptext'], view.view_helptext[step])

    @patch.object(WizardView, 'get_form_kwargs', return_value={})
    def test_get_form_kwargs_select_primary_step(self, _super_mock):
        """
        Assert that get_form_kwargs adds the expected choices for the select
        primary step.
        """
        view = self.get_view(
            queryset=self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk]),
            # The wizard view expects form_list to be a dictionary:
            # (WizardView.get_initkwargs turns the form_list list into an OrderedDict)
            form_list={MergeView.SELECT_PRIMARY_STEP: MergeFormSelectPrimary}
        )
        form_kwargs = view.get_form_kwargs(step=MergeView.SELECT_PRIMARY_STEP)
        self.assertIn('choices', form_kwargs)
        formfield_name = '0-' + MergeFormSelectPrimary.PRIMARY_FIELD_NAME
        self.assertEqual(
            sorted(list(view.queryset.values_list('pk', flat=True))),
            sorted(list(form_kwargs['choices'][formfield_name].values_list('pk', flat=True)))
        )

    @patch.object(WizardView, 'get_form_kwargs', return_value={})
    def test_get_form_kwargs_conflict_step(self, _super_mock):
        """
        Assert that get_form_kwargs adds the expected form data for the conflict
        resolution step.
        """
        view = self.get_view(
            queryset=self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk]),
            # The wizard view expects form_list to be a dictionary:
            # (WizardView.get_initkwargs turns the form_list list into an OrderedDict)
            form_list={MergeView.CONFLICT_RESOLUTION_STEP: MergeConflictsFormSet}
        )
        # Conflict for 'jahrgang':
        view._updates = {'jahrgang': ['1', '2'], 'beschreibung': ['Test']}
        form_kwargs = view.get_form_kwargs(step=MergeView.CONFLICT_RESOLUTION_STEP)
        self.assertIn('data', form_kwargs)
        expected = {
            '1-TOTAL_FORMS': 1, '1-MAX_NUM_FORMS': '', '1-0-original_fld_name': 'jahrgang',
            '1-INITIAL_FORMS': '0', '1-0-verbose_fld_name': 'Jahrgang'
        }
        self.assertEqual(form_kwargs['data'], expected)
        self.assertIn('form_kwargs', form_kwargs)
        self.assertIn('choices', form_kwargs['form_kwargs'])
        self.assertEqual(
            form_kwargs['form_kwargs']['choices'], {'1-0-posvals': [(0, '1'), (1, '2')]}
        )

    def test_action_not_allowed_single_object(self):
        """
        If only one object was selected, the user should be sent back to the
        changelist with an error message.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        expected_message = (
            'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden,'
            ' um diese Aktion durchzuführen.'
        )
        self.assertMessageSent(response.wsgi_request, expected_message)

    def test_action_not_allowed_different_magazin(self):
        """
        If the selected objects are not related to the same magazine instance,
        the user should be sent back to the changelist with an error message.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj3.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        self.assertMessageSent(response.wsgi_request, expected_message)

    def test_post_first_step(self):
        """The first step should be the form to select the primary object."""
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/merge_records.html')
        self.assertIsInstance(response.context['wizard']['form'], MergeFormSelectPrimary)

    def test_post_first_form_valid_and_no_merge_conflict(self):
        """
        Upon a successful merge without conflicts, the user should be returned
        to the changelist.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk],
            # Management form:
            'merge_view-current_step': 0,
            # Form data:
            '0-primary': self.obj1.pk,
            '0-expand_primary': True
        }
        with patch('dbentry.actions.views.merge_records'):
            response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')

    def test_post_second_step(self):
        """The second step should be the form for handling conflicts."""
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk],
            # Management form:
            'merge_view-current_step': 0,
            # Form data:
            '0-primary': self.obj1.pk,
            '0-expand_primary': True
        }
        response = self.post_response(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/merge_records.html')
        self.assertIsInstance(response.context['wizard']['form'], MergeConflictsFormSet)

    def test_post_merge_conflict_handled(self):
        """
        If conflicts were handled successfully, the user should be returned to
        the changelist.
        """
        # Set up the session data for the first step (get_step_data).
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk],
            # Management form:
            'merge_view-current_step': 0,
            # Form data:
            '0-primary': self.obj1.pk,
            '0-expand_primary': True
        }
        self.post_response(self.changelist_path, data=request_data)

        # Handle the merge conflicts:
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk],
            # Management form:
            'merge_view-current_step': 1,
            '1-INITIAL_FORMS': '0',
            '1-MAX_NUM_FORMS': '',
            '1-MIN_NUM_FORMS': '',
            '1-TOTAL_FORMS': '1',
            # Form data:
            '1-0-verbose_fld_name': 'Jahrgang',
            '1-0-original_fld_name': 'jahrgang',
            '1-0-posvals': 0,
        }
        with patch('dbentry.actions.views.merge_records'):
            response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')

    def test_done_error(self):
        """
        Assert that an admin message is sent to user upon encountering a
        ProtectedError during merging.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk],
            # Management form:
            'merge_view-current_step': 0,
            # Form data:
            '0-primary': self.obj1.pk,
            '0-expand_primary': True
        }
        with patch.object(MergeView, 'perform_action') as m:
            m.side_effect = models.deletion.ProtectedError('msg', self.model.objects.all())
            response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertMessageSent(
            response.wsgi_request, 'Folgende verwandte Ausgaben verhinderten die Zusammenführung:'
        )

    @translation_override(language=None)
    def test_permissions_required(self):
        """Assert that specific permissions are required to access this action."""
        # User needs view permission to have access to the change list. User
        # also needs access to at least one action for the action form to be
        # included (here: delete selected action).
        opts = self.model._meta
        ct = ContentType.objects.get_for_model(self.model)
        view_perm = Permission.objects.get(
            codename=get_permission_codename('view', opts), content_type=ct
        )
        delete_perm = Permission.objects.get(
            codename=get_permission_codename('delete', opts), content_type=ct
        )
        self.staff_user.user_permissions.set([view_perm, delete_perm])

        # The action should not be an option in the action form - a request
        # with that action should send us back to the change list with a
        # 'No action selected.' admin message.
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk],
        }
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertMessageSent(response.wsgi_request, 'No action selected.')

        # Give the user the permissions required for the action:
        merge_perm = Permission.objects.get(
            codename=get_permission_codename('merge', opts), content_type=ct
        )
        self.staff_user.user_permissions.add(merge_perm)
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/merge_records.html')

    def test_perform_action_no_expand(self):
        """
        Assert that merge_records is called with expand=False, if
        'expand_primary' on the first form is False.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk],
            # Management form:
            'merge_view-current_step': 0,
            # Form data:
            '0-primary': self.obj1.pk,
            '0-expand_primary': False
        }
        with patch('dbentry.actions.views.merge_records') as merge_mock:
            self.post_response(self.changelist_path, data=request_data, user=self.super_user)
        args, _kwargs = merge_mock.call_args
        # Not interested in the first and second argument. (primary object and queryset)
        self.assertFalse(
            args[2], msg="Third argument 'update_data' should be empty if expand_primary is False."
        )
        self.assertFalse(args[3], msg="Fourth argument 'expand' should be False.")


class TestMergeViewArtikel(ActionViewTestCase):
    admin_site = miz_site
    view_class = MergeView
    model = _models.Artikel
    model_admin_class = _admin.ArtikelAdmin

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, ausgabe=make(_models.Ausgabe))
        cls.obj2 = make(cls.model, ausgabe=make(_models.Ausgabe))
        super().setUpTestData()

    def test_action_allowed_different_ausgabe_instances(self):
        """
        The action should not be allowed, if the Artikel objects are related to
        different Ausgabe objects.
        """
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(response.wsgi_request, expected_message)


class TestMoveToBrochure(ActionViewTestCase):
    admin_site = miz_site
    view_class = MoveToBrochure
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        cls.mag = mag = make(
            _models.Magazin, magazin_name='Testmagazin', beschreibung='Ein Magazin für Tests.'
        )
        cls.obj1 = make(
            cls.model, magazin=mag, beschreibung='Foo', sonderausgabe=True,
            bemerkungen='Do not use in production!', ausgabejahr__jahr=[2000, 2001],
            bestand__extra=1
        )
        cls.other = make(cls.model, magazin__magazin_name='The Other')
        super().setUpTestData()

    def test(self):
        """Test moving Ausgabe objects."""
        # Add some more test data:
        obj2 = make(
            self.model, magazin=self.mag, beschreibung='Bar', ausgabejahr__jahr=[2000, 2001],
            bestand__extra=1
        )
        obj3 = make(self.model, magazin=self.mag)
        bestand1 = self.obj1.bestand_set.first()
        bestand2 = obj2.bestand_set.first()

        # User selects two Ausgabe instances of different magazines and gets a
        # message telling them that the action was aborted:
        action_data = {
            'action': ['moveto_brochure'],
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.other.pk]
        }
        response = self.post_response(self.changelist_path, data=action_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        expected_message = (
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu '
            'unterschiedlichen Magazinen.'
        )
        self.assertMessageSent(response.wsgi_request, expected_message)

        # User selects a single ausgabe and proceeds to the selection:
        action_data[helpers.ACTION_CHECKBOX_NAME] = [self.obj1.pk]
        response = self.post_response(self.changelist_path, data=action_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/movetobrochure.html')

        # User aborts and is directed back to the changelist
        response = self.get_response(path=self.changelist_path)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')

        # User selects another valid ausgabe and returns to the selection with
        # the two instances.
        action_data[helpers.ACTION_CHECKBOX_NAME] = [self.obj1.pk, obj2.pk, obj3.pk]
        response = self.post_response(self.changelist_path, data=action_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/movetobrochure.html')

        # User selects the 'Katalog' category and confirms, without having
        # checked the delete_magazin checkbox.
        management_form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': ''
        }
        request_data = {
            'action_confirmed': 'Ja, ich bin sicher',
            'brochure_art': 'katalog',
            'delete_magazin': False,
            'form-0-titel': 'Foo Katalog',
            'form-0-ausgabe_id': self.obj1.pk,
            'form-0-accept': True,
            'form-1-titel': 'Bar Katalog',
            'form-1-ausgabe_id': obj2.pk,
            'form-1-accept': True,
            'form-2-titel': 'Spam Katalog',
            'form-2-ausgabe_id': obj3.pk,
            'form-2-accept': False,
        }
        request_data.update(action_data)
        request_data.update(management_form_data)
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        # User is redirected back to the changelist:
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        # The magazin should still exist:
        self.assertTrue(_models.Magazin.objects.filter(pk=self.mag.pk).exists())
        # But the Ausgabe instances should have been moved:
        self.assertFalse(_models.Ausgabe.objects.filter(pk__in=[self.obj1.pk, obj2.pk]))
        self.assertTrue(_models.Katalog.objects.filter(titel='Foo Katalog').exists())
        katalog1 = _models.Katalog.objects.get(titel='Foo Katalog')
        self.assertTrue(_models.Katalog.objects.filter(titel='Bar Katalog').exists())
        katalog2 = _models.Katalog.objects.get(titel='Bar Katalog')
        # ...along with the year values...
        self.assertQuerysetEqual(
            katalog1.jahre.values_list('jahr', flat=True),
            ['2000', '2001'], transform=str
        )
        self.assertQuerysetEqual(
            katalog2.jahre.values_list('jahr', flat=True),
            ['2000', '2001'], transform=str
        )
        # ...and the bestand objects...
        bestand1.refresh_from_db()
        bestand2.refresh_from_db()
        self.assertIsNone(bestand1.ausgabe_id)
        self.assertIsNone(bestand2.ausgabe_id)
        self.assertEqual(bestand1.brochure_id, katalog1.pk)
        self.assertEqual(bestand2.brochure_id, katalog2.pk)
        # ...but NOT obj3!
        self.assertTrue(_models.Ausgabe.objects.filter(pk=obj3.pk).exists())

        # User selects another ausgabe and this time also deletes the magazin:
        other_mag = self.other.magazin
        action_data[helpers.ACTION_CHECKBOX_NAME] = [self.other.pk]
        management_form_data['form-TOTAL_FORMS'] = '1'
        request_data = {
            'action_confirmed': 'Ja, ich bin sicher',
            'brochure_art': 'katalog',
            'delete_magazin': True,
            'form-0-titel': 'Other One',
            'form-0-ausgabe_id': self.other.pk,
            'form-0-accept': True
        }
        request_data.update(action_data)
        request_data.update(management_form_data)
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertFalse(_models.Magazin.objects.filter(pk=other_mag.pk).exists())
        # User is redirected back to the changelist:
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        # The other magazin should have been deleted:
        self.assertFalse(_models.Magazin.objects.filter(pk=other_mag.pk).exists())

    def test_action_allowed_has_artikels(self):
        """
        The action should not be allowed, if any of selected objects are
        referenced by Artikel objects.
        """
        make(_models.Artikel, ausgabe=self.obj1)
        request_data = {
            'action': 'moveto_brochure',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        expected_message = (
            'Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht '
            'verschoben werden können: '
            f'<a href="/admin/dbentry/ausgabe/{self.obj1.pk}/change/">Foo</a>'
        )
        self.assertMessageSent(response.wsgi_request, expected_message)

    def test_action_allowed_not_same_magazin(self):
        """
        The action should not be allowed, if the selected objects are not
        related to the same Magazin object.
        """
        request_data = {
            'action': 'moveto_brochure',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.other.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertMessageSent(
            response.wsgi_request,
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        )

    def test_get_initial(self):
        """Check the initial form data."""
        view = self.get_view(queryset=self.model.objects.filter(pk=self.obj1.pk))
        initial = view.get_initial()
        self.assertEqual(len(initial), 1)
        self.assertEqual(initial[0]['ausgabe_id'], self.obj1.pk)
        self.assertEqual(initial[0]['titel'], f'Testmagazin {self.obj1}')
        self.assertEqual(initial[0]['zusammenfassung'], 'Ein Magazin für Tests.')
        self.assertEqual(initial[0]['beschreibung'], 'Foo')
        self.assertEqual(initial[0]['bemerkungen'], 'Do not use in production!')

    def test_options_form_invalid(self):
        """Assert that form_valid checks if the options form is also valid."""
        request = self.post_request(data={'brochure_art': 'invalid', 'delete_magazin': False})
        view = self.get_view(request, queryset=self.queryset)
        form = forms.Form()
        form.is_valid()
        with patch.object(view, 'render_to_response') as render_mock:
            response = view.form_valid(form)
        render_mock.assert_called()
        self.assertIsNotNone(response)

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action(self, get_model_mock, *_mocks):
        """Check that perform_action moves the objects as expected."""
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        obj2 = make(self.model, magazin=self.mag)
        form_data = [
            {
                'titel': 'Foo Brochure',
                'ausgabe_id': self.obj1.pk,
                'accept': True,
                'zusammenfassung': 'Alice likes to read them.',
                'beschreibung': ''  # obj1's Beschreibung was removed
            },
            {
                'titel': 'Do not move me',
                'ausgabe_id': obj2.pk,
                'accept': False,
            }
        ]
        options_form_data = {'brochure_art': target_model._meta.model_name, 'delete_magazin': False}
        view = self.get_view(
            self.get_request(),
            queryset=self.model.objects.filter(pk__in=[self.obj1.pk, obj2.pk])
        )
        view._magazin_instance = self.mag

        changed_bestand = self.obj1.bestand_set.first()  # snapshot the bestand
        view.perform_action(form_data, options_form_data)
        self.assertTrue(target_model.objects.filter(titel='Foo Brochure').exists())
        new_brochure = target_model.objects.get(titel='Foo Brochure')

        # Inspect the brochure attributes:
        self.assertEqual(new_brochure.zusammenfassung, 'Alice likes to read them.')
        self.assertFalse(new_brochure.beschreibung)
        # Inspect the bestand:
        changed_bestand.refresh_from_db()
        self.assertIsNone(changed_bestand.ausgabe_id)
        self.assertEqual(changed_bestand.brochure_id, new_brochure.pk)
        # Assert that the obj1 Ausgabe was deleted:
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())
        # Assert that the ob2 Ausgabe was not moved:
        self.assertTrue(self.model.objects.filter(pk=obj2.pk).exists())
        self.assertFalse(target_model.objects.filter(titel='Do not move me').exists())

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_ausgabe_does_not_exist(self, get_model_mock, *_mocks):
        """Assert that perform_action can handle invalid data for 'ausgabe_id'."""
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': '0',
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        with self.assertNotRaises(_models.Ausgabe.DoesNotExist):
            view.perform_action(form_data, options_form_data)

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_deletes_magazin(self, get_model_mock, *_mocks):
        """Assert that perform_action can delete the related magazin object."""
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name, 'delete_magazin': True}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        view.perform_action(form_data, options_form_data)
        self.assertFalse(_models.Magazin.objects.filter(pk=self.mag.pk).exists())

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_not_deletes_magazin(self, get_model_mock, *_mocks):
        """
        Assert that perform_action does not delete the magazin object, if the
        user does not want to delete it.
        """
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name, 'delete_magazin': False}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        view.perform_action(form_data, options_form_data)
        self.assertTrue(_models.Magazin.objects.filter(pk=self.mag.pk).exists())

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_moves_jahre(self, get_model_mock, *_mocks):
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name, 'delete_magazin': False}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        view.perform_action(form_data, options_form_data)
        new_brochure = target_model.objects.get()
        self.assertQuerysetEqual(
            new_brochure.jahre.values_list('jahr', flat=True),
            ['2000', '2001'], transform=str
        )

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_adds_creation_hints(self, get_model_mock, *_mocks):
        """
        Assert that perform_action adds log entry objects that explain how the
        new Brochure object was created.
        """
        target_model = _models.Brochure
        target_opts = target_model._meta
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_opts.model_name, 'delete_magazin': False}

        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag
        expected = (
            f"Hinweis: {target_opts.verbose_name} wurde automatisch erstellt beim "
            f"Verschieben von Ausgabe {self.obj1!s} (Magazin: {self.obj1.magazin!s})."
        )
        view.perform_action(form_data, options_form_data)
        new_brochure = target_model.objects.get()
        ct = ContentType.objects.get_for_model(target_model)
        logentry = LogEntry.objects.get(object_id=new_brochure.pk, content_type=ct)
        self.assertEqual(logentry.get_change_message(), expected)

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_katalog(self, get_model_mock, *_mocks):
        """Assert that perform_action moves Ausgabe instances to the model 'Katalog'."""
        target_model = _models.Katalog
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Katalog',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        changed_bestand = self.obj1.bestand_set.first()
        view.perform_action(form_data, options_form_data)
        self.assertTrue(target_model.objects.filter(titel='Foo Katalog').exists())
        new_brochure = target_model.objects.get(titel='Foo Katalog')

        # Check the value for the 'art' field specific to Katalog:
        self.assertEqual(new_brochure.art, _models.Katalog.Types.MERCH)
        # Inspect the bestand:
        changed_bestand.refresh_from_db()
        self.assertIsNone(changed_bestand.ausgabe_id)
        self.assertEqual(changed_bestand.brochure_id, new_brochure.pk)
        # Assert that the obj1 Ausgabe was deleted:
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_kalender(self, get_model_mock, *_mocks):
        """Assert that perform_action moves Ausgabe instances to the model 'Kalender'."""
        target_model = _models.Kalender
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Kalender',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        changed_bestand = self.obj1.bestand_set.first()
        view.perform_action(form_data, options_form_data)
        self.assertTrue(target_model.objects.filter(titel='Foo Kalender').exists())
        new_brochure = target_model.objects.get(titel='Foo Kalender')

        # Inspect the bestand:
        changed_bestand.refresh_from_db()
        self.assertIsNone(changed_bestand.ausgabe_id)
        self.assertEqual(changed_bestand.brochure_id, new_brochure.pk)
        # Assert that the obj1 Ausgabe was deleted:
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected')
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_protected_ausgabe(self, get_model_mock, protected_mock, *_mocks):
        """
        Assert that perform_action does not create Brochure objects for
        protected Ausgabe objects.
        """
        target_model = _models.Brochure
        get_model_mock.return_value = target_model
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': target_model._meta.model_name}
        # Get a request that went through the 'messages' middleware:
        request = self.get_response('/').wsgi_request
        view = self.get_view(request, queryset=self.queryset)
        view._magazin_instance = self.mag

        # Do two tests. One where the transaction never happens because
        # is_protected returned True, and one where the transaction was rolled
        # back due to a ProtectedError exception.
        for is_protected_return_value in (True, False):
            protected_mock.return_value = is_protected_return_value
            if not is_protected_return_value:
                # Add an Artikel object to protect the Ausgabe object.
                make(_models.Artikel, ausgabe_id=self.obj1.pk)
            with self.subTest(is_protected_return_value=is_protected_return_value):
                view.perform_action(form_data, options_form_data)
                self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
                self.assertFalse(target_model.objects.filter(titel='Foo Brochure').exists())
                expected_message = (
                    'Folgende Ausgaben konnten nicht gelöscht werden: '
                    f'<a href="/admin/dbentry/ausgabe/{self.obj1.pk}/change/" target="_blank">{self.obj1!s}</a> '  # noqa
                    f'(<a href="/admin/dbentry/ausgabe/?id__in={self.obj1.pk}" target="_blank">Liste</a>). '  # noqa
                    'Es wurden keine Broschüren für diese Ausgaben erstellt.'
                )
                self.assertMessageSent(request, expected_message)

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_does_not_roll_back_ausgabe_deletion(self, get_model_mock, *_mocks):
        """
        Assert that a rollback on the transaction that deletes the magazin does
        not also roll back the changes made to Ausgabe or Brochure objects.
        """
        get_model_mock.return_value = _models.Brochure
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': True,
        }]
        options_form_data = {'brochure_art': 'brochure', 'delete_magazin': True}
        # Get a request that went through the 'messages' middleware:
        request = self.get_response('/').wsgi_request
        view = self.get_view(request, queryset=self.queryset)
        # Add another Ausgabe object to the Magazin object to protect it:
        make(self.model, magazin=self.mag)
        view._magazin_instance = self.mag

        view.perform_action(form_data, options_form_data)
        # The creation of Brochure/deletion of Ausgabe objects should have gone
        # through:
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())
        self.assertTrue(_models.Brochure.objects.filter(titel='Foo Brochure').exists())
        # But the Magazin object should still exist:
        self.assertTrue(_models.Magazin.objects.filter(pk=self.mag.pk).exists())
        self.assertMessageSent(request, 'Magazin konnte nicht gelöscht werden: ')

    @patch('dbentry.actions.views.log_change')
    @patch('dbentry.actions.views.log_deletion')
    @patch('dbentry.actions.views.create_logentry')
    @patch('dbentry.actions.views.is_protected', new=Mock(return_value=False))
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_not_accepted(self, get_model_mock, *_mocks):
        """Assert that an ausgabe is not changed if the user unticks 'accept'."""
        get_model_mock.return_value = _models.Brochure
        form_data = [{
            'titel': 'Foo Brochure',
            'ausgabe_id': self.obj1.pk,
            'accept': False,
        }]
        options_form_data = {'brochure_art': 'brochure'}
        view = self.get_view(self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        view.perform_action(form_data, options_form_data)
        self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
        self.assertFalse(_models.Brochure.objects.filter(titel='Foo Brochure').exists())

    @patch('dbentry.actions.views.get_obj_link')
    def test_context_contains_forms(self, *_mocks):
        """
        Assert that the formset, management form and the options form are
        included in the template context.
        """
        view = self.get_view(self.get_request())
        context = view.get_context_data()

        self.assertIsInstance(context['form'], BrochureActionFormSet)
        self.assertIsInstance(context['management_form'], ManagementForm)
        self.assertIsInstance(context['options_form'], BrochureActionFormOptions)

    @patch('dbentry.actions.views.MoveToBrochure.can_delete_magazin', new_callable=PropertyMock)
    def test_conditionally_show_delete_magazin_option(self, can_delete_mock):
        """
        Assert that the field 'delete_magazin' is only enabled on the
        options_form, if the magazin can be deleted.
        """
        view = self.get_view()
        for can_be_deleted in (True, False):
            with self.subTest(can_be_deleted=can_be_deleted):
                can_delete_mock.return_value = can_be_deleted
                form = view.get_options_form()
                if can_be_deleted:
                    self.assertFalse(form.fields['delete_magazin'].disabled)
                else:
                    self.assertTrue(form.fields['delete_magazin'].disabled)

    def test_can_delete_magazin(self):
        """
        Assert that can_delete_magazin returns True, if all Ausgabe instance of
        the main Magazin instances are included in the action queryset.
        """
        view = self.get_view(queryset=self.model.objects.filter(pk=self.obj1.pk))
        view._magazin_instance = self.mag
        self.assertTrue(view.can_delete_magazin)

    def test_can_not_delete_magazin(self):
        """
        Assert that can_delete_magazin returns False, if not all Ausgabe
        instance of the main Magazin instances are included in the action
        queryset.
        """
        # Add another related Ausgabe object to the Magazin instance, but do
        # not include it in the request.
        make(self.model, magazin=self.mag)
        view = self.get_view(queryset=self.model.objects.filter(pk=self.obj1.pk))
        view._magazin_instance = self.mag
        self.assertFalse(view.can_delete_magazin)

    @translation_override(language=None)
    def test_permissions_required(self):
        """Assert that specific permissions are required to access this action."""
        # User needs view permission to have access to the change list. User
        # also needs access to at least one action for the action form to be
        # included (here: delete selected action).
        opts = self.model._meta
        ct = ContentType.objects.get_for_model(self.model)
        view_perm = Permission.objects.get(
            codename=get_permission_codename('view', opts), content_type=ct
        )
        delete_perm = Permission.objects.get(
            codename=get_permission_codename('delete', opts), content_type=ct
        )
        self.staff_user.user_permissions.set([view_perm, delete_perm])

        # The action should not be an option in the action form - a request
        # with that action should send us back to the change list with a
        # 'No action selected.' admin message.
        request_data = {
            'action': 'moveto_brochure',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
        }
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertMessageSent(response.wsgi_request, 'No action selected.')

        # Give the user the permissions required for the action:
        add_perm = Permission.objects.get(
            codename=get_permission_codename('add', _models.BaseBrochure._meta),
            content_type=ContentType.objects.get_for_model(_models.BaseBrochure)
        )
        delete_perm = Permission.objects.get(
            codename=get_permission_codename('delete', opts), content_type=ct
        )
        self.staff_user.user_permissions.add(add_perm, delete_perm)
        response = self.post_response(
            self.changelist_path, data=request_data, user=self.staff_user, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/movetobrochure.html')


class TestChangeBestand(ActionViewTestCase, LoggingTestMixin):
    admin_site = miz_site
    view_class = ChangeBestand
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin
    action_name = 'change_bestand'

    @classmethod
    def setUpTestData(cls):
        cls.lagerort1 = make(_models.Lagerort)
        cls.lagerort2 = make(_models.Lagerort)
        mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj1 = make(cls.model, magazin=mag)
        super().setUpTestData()

    @staticmethod
    def get_form_data(parent_obj: _models.Ausgabe, *bestand_objects):
        prefix = 'bestand_set-%s' % parent_obj.pk
        management_form_data = {
            prefix + '-TOTAL_FORMS': len(bestand_objects),
            prefix + '-INITIAL_FORMS': parent_obj.bestand_set.count(),
            prefix + '-MIN_NUM_FORMS': 0,
            prefix + '-MAX_NUM_FORMS': 1000,
        }
        form_data = {}
        for i, (bestand_obj_pk, lagerort_pk) in enumerate(bestand_objects):
            form_prefix = prefix + '-%s' % i
            form_data.update(
                {
                    form_prefix + '-ausgabe': parent_obj.pk,
                    form_prefix + '-signatur': bestand_obj_pk or '',
                    form_prefix + '-lagerort': lagerort_pk or ''
                }
            )
        return {**management_form_data, **form_data}

    def test_success_add(self):
        """Assert that Bestand instances can be added to obj1's bestand_set."""
        response = self.post_response(
            path=self.changelist_path,
            data={
                'action': 'change_bestand',
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
                'action_confirmed': 'Yes',
                **self.get_form_data(self.obj1, (None, self.lagerort1.pk))
            },
            follow=True
        )
        # A successful action should send us back to the changelist:
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        bestand_set = self.obj1.bestand_set
        self.assertEqual(bestand_set.count(), 1)
        self.assertEqual(bestand_set.get().lagerort, self.lagerort1)

    def test_success_update(self):
        """Assert that Bestand instances in obj1's bestand_set can be updated."""
        b = _models.Bestand(lagerort=self.lagerort1, ausgabe=self.obj1)
        b.save()
        response = self.post_response(
            path=self.changelist_path,
            data={
                'action': 'change_bestand',
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
                'action_confirmed': 'Yes',
                **self.get_form_data(self.obj1, (b.pk, self.lagerort2.pk))
            },
            follow=True
        )
        # A successful action should send us back to the changelist:
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_list.html')
        bestand_set = self.obj1.bestand_set
        self.assertEqual(bestand_set.count(), 1)
        self.assertEqual(bestand_set.get().lagerort, self.lagerort2)

    def test_success_delete(self):
        """Assert that Bestand relations can be deleted."""
        b = _models.Bestand(lagerort=self.lagerort1, ausgabe=self.obj1)
        b.save()
        form_data = self.get_form_data(self.obj1, (b.pk, self.lagerort1.pk))
        form_data['bestand_set-%s-0-DELETE' % self.obj1.pk] = True
        response = self.client.post(
            path=self.changelist_path,
            data={
                'action': 'change_bestand',
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
                'action_confirmed': 'Yes',
                **form_data
            },
            follow=False
        )
        self.assertEqual(
            response.status_code, 302,
            msg="Expected a redirect back to the changelist."
        )
        self.assertFalse(self.obj1.bestand_set.exists())

    def test_post_stops_on_invalid(self):
        """A post request with invalid formsets should not post successfully."""
        # Two formsets, of which the second has an invalid lagerort:
        form_data = self.get_form_data(self.obj1, (None, self.lagerort1.pk), (None, -1))
        response = self.client.post(
            path=self.changelist_path,
            data={
                'action': 'change_bestand',
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
                'action_confirmed': 'Yes',
                **form_data
            },
            follow=False
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')

    def test_get_bestand_formset(self):
        """Check that get_bestand_formset returns the expected formset & inline."""
        b = _models.Bestand(lagerort=self.lagerort1, ausgabe=self.obj1)
        b.save()
        request = self.post_request(
            path=self.changelist_path,
            data={'action': 'change_bestand', helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]}
        )
        view = self.get_view(request)
        formset, inline = view.get_bestand_formset(request, self.obj1)
        # Check some attributes of the formset/inline.
        self.assertEqual(inline.model, _models.Bestand)
        self.assertEqual(formset.instance, self.obj1)
        self.assertQuerysetEqual(formset.queryset.all(), self.obj1.bestand_set.all())

    def test_get_bestand_formset_form_data(self):
        """
        Assert that get_bestand_formset only adds formset data, if the keyword
        'action_confirmed' is present in the request.
        """
        request_data = {'action': 'change_bestand', helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]}
        request = self.post_request(path=self.changelist_path, data=request_data)
        view = self.get_view(request)
        formset, inline = view.get_bestand_formset(request, self.obj1)
        self.assertFalse(formset.data)

        request_data['action_confirmed'] = '1'
        request = self.post_request(
            path=self.changelist_path,
            data={
                **request_data,
                **self.get_form_data(self.obj1, (None, self.lagerort1.pk))
            }
        )
        formset, inline = view.get_bestand_formset(request, self.obj1)
        self.assertTrue(formset.data)

    @patch('dbentry.actions.views.get_obj_link')
    def test_media(self, *_mocks):
        """Assert that the formset's media is added to the context."""
        other = make(self.model)
        response = self.post_response(
            path=self.changelist_path,
            data={
                'action': 'change_bestand',
                # Use a queryset with two objects to check the coverage on that
                # 'media_updated condition'.
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, other.pk],
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('admin/js/inlines.js', response.context['media']._js)

    def test_get_bestand_formset_no_inline(self):
        """
        Assert that get_bestand_formset raises an error when no inline class
        was declared for the Bestand model.
        """
        mocked_inlines = Mock(return_value=[])
        with patch.object(self.model_admin, 'get_formsets_with_inlines', new=mocked_inlines):
            request = self.get_request()
            view = self.get_view(self.get_request())
            with self.assertRaises(ValueError):
                view.get_bestand_formset(request, None)

    def test_create_log_entries(self):
        """
        Assert that LogEntry objects are created for the parent object and its
        related objects.
        """
        # Add 3 bestand objects to obj1; one that will remain unchanged, one
        # that will be changed and one that will be deleted. Then, using the
        # action, add a new bestand object to obj1.
        unchanged = make(_models.Bestand, lagerort=self.lagerort1, ausgabe=self.obj1)
        changed = make(_models.Bestand, lagerort=self.lagerort1, ausgabe=self.obj1)
        deleted = make(_models.Bestand, lagerort=self.lagerort1, ausgabe=self.obj1)

        form_data = self.get_form_data(
            self.obj1,
            (unchanged.pk, unchanged.lagerort.pk),
            (changed.pk, self.lagerort2.pk),
            (deleted.pk, deleted.lagerort.pk),
            (None, self.lagerort1.pk)
        )
        form_data['bestand_set-%s-2-DELETE' % self.obj1.pk] = True

        patches = {
            'log_addition': DEFAULT,
            'log_change': DEFAULT,
            'log_deletion': DEFAULT,
        }
        with patch.multiple('dbentry.actions.views', **patches) as mocks:
            with patch('dbentry.admin.AusgabenAdmin.log_change') as admin_log_change:
                self.post_response(
                    path=self.changelist_path,
                    data={
                        'action': 'change_bestand',
                        helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
                        'action_confirmed': 'Yes',
                        **form_data
                    },
                    follow=False
                )
        added = _models.Bestand.objects.order_by('-pk').first()
        changed.refresh_from_db()

        # Check the log entry for the parent instance:
        name = _models.Bestand._meta.verbose_name
        expected_change_message = [
            {'added': {'name': name, 'object': str(added)}},
            {'changed': {'name': name, 'object': str(changed), 'fields': ['lagerort']}},
            {'deleted': {'name': name, 'object': str(deleted)}}
        ]
        admin_log_change.assert_called()
        _request, formset_instance, change_message = admin_log_change.call_args[0]
        self.assertEqual(formset_instance, self.obj1)
        self.assertEqual(change_message, expected_change_message)

        # Check the log entries for the Bestand instances:
        mocks['log_addition'].assert_called_with(self.super_user.pk, added)
        mocks['log_change'].assert_called_with(self.super_user.pk, changed, fields=['lagerort'])
        # Can't compare the instances (second argument) directly, since one of
        # them has been deleted.
        args, kwargs = mocks['log_deletion'].call_args
        self.assertEqual((args[0], str(args[1])), (self.super_user.pk, str(deleted)))


@override_settings(ROOT_URLCONF='tests.test_actions.urls')
class TestReplace(ActionViewTestCase, LoggingTestMixin):
    action_name = 'replace'
    admin_site = admin_site
    model = Genre
    model_admin_class = GenreAdmin
    view_class = Replace

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(Genre)
        cls.obj2 = make(Genre)
        cls.band = make(Band, genres=[cls.obj1])
        super().setUpTestData()

    @patch('dbentry.actions.views.Replace.admin_site', new=admin_site)
    def test(self):
        request_data = {
            'action': self.action_name,
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/action_confirmation.html')

        # Fill out the form. We should be redirected back to the changelist,
        # and obj1 should have been replaced and deleted.
        request_data['action_confirmed'] = '1'
        request_data['replacements'] = [str(self.obj2.pk)]
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, 'admin/action_confirmation.html')
        self.assertTemplateUsed(response, 'admin/change_list.html')
        self.assertQuerysetEqual(self.band.genres.all(), [self.obj2])

    @patch('dbentry.actions.views.Replace.admin_site', new=admin_site)
    def test_can_only_select_one(self):
        """Assert that the action can only be called with one selected object."""
        request_data = {
            'action': self.action_name,
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, 'admin/action_confirmation.html')
        self.assertMessageSent(
            response.wsgi_request,
            'Diese Aktion kann nur mit einzelnen Datensätzen durchgeführt werden: '
            'bitte wählen Sie nur einen Datensatz aus.'
        )

    def test_adds_log_entries(self):
        """
        Assert that LogEntry change messages are added to the related objects
        that were changed.
        """
        request_data = {
            'action': self.action_name,
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk],
            'action_confirmed': '1',
            'replacements': [str(self.obj2.pk)],
        }
        self.post_response(self.changelist_path, data=request_data, follow=True)
        change_message = [
            {'deleted': {'object': str(self.obj1), 'name': 'Genre'}},
            {'added': {'object': str(self.obj2), 'name': 'Genre'}},
        ]
        self.assertLoggedChange(self.band, change_message=change_message)

    @patch('dbentry.actions.views.Replace.admin_site', new=admin_site)
    def test_requires_superuser_permission(self):
        request_data = {
            'action': self.action_name,
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk]
        }

        response = self.post_response(
            self.changelist_path, user=self.staff_user, data=request_data, follow=True
        )
        self.assertEqual(response.status_code, 403)
        # As superuser:
        response = self.post_response(
            self.changelist_path, user=self.super_user, data=request_data, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_check_one_object_only(self):
        for qs in (self.model.objects.all(), (self.model.objects.filter(pk=self.obj1.pk))):
            with self.subTest(count=qs.count()):
                # Get a request that went through the 'messages' middleware:
                request = self.get_response('/').wsgi_request
                view = self.get_view(queryset=qs, request=request)
                if qs.count() == 1:
                    self.assertTrue(view._check_one_object_only())
                else:
                    self.assertFalse(view._check_one_object_only())
                    self.assertMessageSent(
                        request,
                        'Diese Aktion kann nur mit einzelnen Datensätzen durchgeführt werden: '
                        'bitte wählen Sie nur einen Datensatz aus.'
                    )

    def test_get_form_kwargs_sets_choices(self):
        """Assert that get_form_kwargs adds the choices for the replacements choice field."""
        view = self.get_view(request=self.get_request())
        form_kwargs = view.get_form_kwargs()
        self.assertIn('choices', form_kwargs)
        self.assertIn('replacements', form_kwargs['choices'])
        self.assertQuerysetEqual(
            form_kwargs['choices']['replacements'],
            self.model.objects.all(),
            ordered=False
        )

    def test_get_perform_action_genre(self):
        view = self.get_view(
            request=self.get_request(),
            queryset=self.model.objects.filter(pk=self.obj1.pk)
        )
        view.perform_action(cleaned_data={'replacements': [str(self.obj2.pk)]})
        self.assertQuerysetEqual(self.band.genres.all(), [self.obj2])
        change_message = [
            {'deleted': {'object': str(self.obj1), 'name': 'Genre'}},
            {'added': {'object': str(self.obj2), 'name': 'Genre'}},
        ]
        self.assertLoggedChange(self.band, change_message=change_message)

    def test_perform_action_band(self):
        replacement = make(Band)
        audio = make(Audio, bands=[self.band])

        view = self.get_view(
            request=self.get_request(),
            model_admin=BandAdmin(Band, self.admin_site),
            queryset=Band.objects.filter(pk=self.band.pk)
        )
        view.perform_action(cleaned_data={'replacements': [str(replacement.pk)]})
        self.assertQuerysetEqual(audio.bands.all(), [replacement])
        change_message = [
            {'deleted': {'object': str(self.band), 'name': 'Band'}},
            {'added': {'object': str(replacement), 'name': 'Band'}},
        ]
        self.assertLoggedChange(audio, change_message=change_message)

    def test_get_objects_list_genre(self):
        """
        Assert that get_objects_list returns links to the objects that are
        related to the object to be replaced.
        """
        opts = Band._meta
        url = reverse(
            f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_change",
            args=[self.band.pk]
        )
        link = f'<a href="{url}" target="_blank">{self.band}</a>'

        view = self.get_view(
            request=self.get_request(),
            queryset=self.model.objects.filter(pk=self.obj1.pk)
        )
        self.assertEqual(view.get_objects_list(), [(f'Band: {link}',)])

    def test_get_objects_list_band(self):
        """
        Assert that get_objects_list can handle reverse relations declared on
        the model of the object to be replaced.
        """
        # When replacing a Band object, the related Audio object should be
        # included in the objects_list:
        _replacement = make(Band)
        audio = make(Audio, bands=[self.band])
        opts = Audio._meta
        url = reverse(
            f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_change",
            args=[audio.pk]
        )
        link = f'<a href="{url}" target="_blank">{audio}</a>'

        view = self.get_view(
            request=self.get_request(),
            model_admin=BandAdmin(Band, self.admin_site),
            queryset=Band.objects.filter(pk=self.band.pk)
        )
        self.assertIn((f'Audio-Material: {link}',), view.get_objects_list())

    @patch('dbentry.actions.views.Replace.admin_site', new=admin_site)
    def test_get_context_data(self):
        view = self.get_view(
            request=self.get_request(),
            queryset=self.model.objects.filter(pk=self.obj1.pk),
        )
        helptext = (
            f'Ersetze Genre "{self.obj1}" durch die unten ausgewählten Genres. '
            f'Dabei werden auch die Datensätze verändert, die mit "{self.obj1}" verwandt sind.'
        )
        expected = [
            ('title', 'Genre ersetzen'),
            ('objects_name', 'Datensätze'),
            ('view_helptext', helptext)
        ]
        context = view.get_context_data()
        for key, value in expected:
            with self.subTest(key=key):
                self.assertIn(key, context)
                self.assertEqual(context[key], value)
