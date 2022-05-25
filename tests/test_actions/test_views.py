from unittest import expectedFailure, skip
from unittest.mock import call, patch, Mock, PropertyMock, DEFAULT

from django import forms
from django.urls import path
from django.utils.html import format_html
from django.views.generic.base import ContextMixin, View
from formtools.wizard.views import SessionWizardView, WizardView

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import tag, override_settings
from django.utils.translation import override as translation_override

import dbentry.models as _models
from dbentry.admin import BandAdmin, AusgabenAdmin, ArtikelAdmin, AudioAdmin
from dbentry.actions.base import (
    ActionConfirmationView, ConfirmationViewMixin, WizardConfirmationView)
from dbentry.actions.views import (
    BulkEditJahrgang, MergeViewWizarded, MoveToBrochureBase,
    ChangeBestand
)
from dbentry.actions.forms import (
    MergeConflictsFormSet, MergeFormSelectPrimary, BrochureActionFormOptions)
from dbentry.base.forms import MIZAdminForm
from dbentry.base.views import MIZAdminMixin, FixedSessionWizardView
from dbentry.sites import miz_site
from dbentry.tests.mixins import LoggingTestMixin
from dbentry.utils import get_obj_link
from tests.case import AdminTestCase, ViewTestCase
from tests.factory import make
from tests.test_actions.models import Band, Genre


admin_site = admin.AdminSite(name='test')


class RenameConfirmationForm(MIZAdminForm):
    new_name = forms.CharField()


class RenameBandActionView(ActionConfirmationView):
    """Dummy action view class."""

    title = 'Rename Band'
    breadcrumbs_title = 'Rename'
    # TODO: check for that 'reversible' specific stuff?
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
    pass


class URLConf:
    urlpatterns = [path('test_actions/', admin_site.urls)]


@override_settings(ROOT_URLCONF=URLConf)
class Test(AdminTestCase):
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
            'index': '0',  # index which action form was posted (f.ex. 0=top, 1=bottom)
            helpers.ACTION_CHECKBOX_NAME: [str(self.obj.pk)]  # selected objects
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'admin/action_confirmation.html')

        # Add form data and confirm the action:
        request_data['new_name'] = 'RENAMED'
        request_data['action_confirmed'] = '1'
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Should have been returned to the changelist:
        self.assertEqual(response.templates[0].name, 'admin/change_list.html')
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.band_name, 'RENAMED')

    def test_action_not_allowed(self):
        """The user should be redirected back to the changelist, if the action is not allowed."""
        request_data = {
            'action': 'rename_band',
            'index': '0',  # index which action form was posted (f.ex. 0=top, 1=bottom)
            helpers.ACTION_CHECKBOX_NAME: [str(self.inactive.pk)]  # selected objects
        }
        response = self.post_response(self.changelist_path, data=request_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'admin/change_list.html')


class ActionViewTestCase(AdminTestCase, ViewTestCase):

    action_name = ''

    def get_view(self, request=None, args=None, kwargs=None, action_name=None, **initkwargs):
        # Allow setting the action_name and fields attribute and assure
        # model_admin and queryset are passed as initkwargs.
        initkwargs = {
            'model_admin': self.model_admin, 'queryset': self.queryset.all(),
            'action_name': action_name or self.action_name, **initkwargs
        }
        #
        action_name = action_name or self.action_name  # TODO: add action_name to initkwargs - might have the same effect?
        if action_name:
            self.view_class.action_name = action_name

        return super().get_view(request=request, args=args, kwargs=kwargs, **initkwargs)


def outside_check(view):
    return True


@override_settings(ROOT_URLCONF=URLConf)
class TestConfirmationViewMixin(ActionViewTestCase):

    class DummyView(ConfirmationViewMixin, ContextMixin, View):
        admin_site = admin_site
        action_allowed_checks = ['not_callable', 'check_true', outside_check]
        not_callable = ()

        def check_true(view):  # noqa
            return True

        def check_false(view):  # noqa
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
        # noinspection PyUnresolvedReferences
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
        view.title = 'Merge Bands'
        view.breadcrumbs_title = 'Merging'
        view.non_reversible_warning = 'This action cannot be reversed.'

        context = view.get_context_data()
        self.assertEqual(context['title'], 'Merge Bands')
        self.assertEqual(context['breadcrumbs_title'], 'Merging')
        self.assertEqual(context['non_reversible_warning'], 'This action cannot be reversed.')

    @expectedFailure
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


def get_obj_link(obj, user, site_name, blank):
    """Mock version of dbentry.admin.utils.get_obj_link"""
    target = ''
    if blank:
        target = format_html(' target="_blank"')
    return format_html('<a href="URL"{target}>{obj}</a>', target=target, obj=obj)


class DummyForm(forms.Form):
    pass


@override_settings(ROOT_URLCONF=URLConf)
class TestActionConfirmationView(ActionViewTestCase):

    class DummyView(ActionConfirmationView):
        admin_site = admin_site
        form_class = DummyForm  # ActionConfirmationView is a FormView'

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

    @patch('dbentry.actions.base.get_obj_link')
    def test_compile_affected_objects(self, get_link_mock):
        get_link_mock.side_effect = get_obj_link
        view = self.get_view(
            self.get_request(),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),
            affected_fields=['band_name', 'genres', 'status']
        )
        user = view.request.user
        link_list = view.compile_affected_objects()

        # link_list should have a structure like this:
        # [
        #       ('Band: <link of obj1>', [<affected objects>]),
        #       ('Band: <link of obj2>', [<affected objects>]),
        #       ...
        # ]

        self.assertEqual(
            len(get_link_mock.call_args_list), 3,
            msg="Expected get_obj_link to be called three times, as three links are expected."
        )
        self.assertEqual(link_list[0][0], f'Band: <a href="URL" target="_blank">{self.obj}</a>')
        # Note that the link for the object is created after the links of its 
        # related objects. That means it is the last mock call.
        self.assertEqual(
            get_link_mock.call_args_list[-1], call(self.obj, user, self.admin_site.name, blank=True)
        )

        # link_list[0][1] is the list of values for the affected fields:
        affected_field_values = link_list[0][1]
        self.assertEqual(affected_field_values[0], 'Bandname: ' + self.obj.band_name)
        
        # The next two items should be links to the Genre objects:
        genres = Genre.objects.all().order_by('genre')
        self.assertEqual(
            affected_field_values[1], f'Genre: <a href="URL" target="_blank">{genres[0]}</a>'
        )
        self.assertEqual(
            get_link_mock.call_args_list[0],
            call(genres[0], user, self.admin_site.name, blank=True)
        )
        self.assertEqual(
            affected_field_values[2], f'Genre: <a href="URL" target="_blank">{genres[1]}</a>'
        )
        self.assertEqual(
            get_link_mock.call_args_list[1],
            call(genres[1], user, self.admin_site.name, blank=True)
        )
        
        # And the last item should be the status:
        self.assertEqual(link_list[0][1][3], 'Status: Aktiv')

    @patch('dbentry.actions.base.get_obj_link')
    def test_compile_affected_objects_no_affected_fields(self, get_link_mock):
        get_link_mock.return_value = format_html('<a href="URL">a link</a>')
        view = self.get_view(
            self.get_request(),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),
            affected_fields=[]
        )
        self.assertEqual(view.compile_affected_objects(), [('Band: <a href="URL">a link</a>',)])

    @patch('dbentry.actions.base.get_obj_link')
    def test_compile_affected_objects_no_link(self, get_link_mock):
        """Assert that a string representation of the object is presented, if
        no link could be created for it.
        """
        get_link_mock.return_value = f'Band: {self.obj}'
        view = self.get_view(
            self.get_request(),
            model_admin=self.model_admin,
            queryset=self.model.objects.all(),
            affected_fields=[]
        )
        self.assertEqual(view.compile_affected_objects(), [(f'Band: {self.obj}', )])

    def test_form_valid(self):
        """
        Assert that form_valid returns None to redirect the user back to the
        changelist.
        """
        view = self.get_view()
        view.perform_action = Mock()
        self.assertIsNone(view.form_valid(Mock()))

    def test_get_context_data_adds_affected_objects(self):
        """Assert that 'affected_objects' are added to the context data."""
        view = self.get_view(self.get_request())
        with patch.object(view, 'compile_affected_objects'):
            self.assertIn('affected_objects', view.get_context_data())


@override_settings(ROOT_URLCONF=URLConf)
class TestWizardConfirmationView(ActionViewTestCase):

    admin_site = admin_site
    view_class = WizardConfirmationView
    model = Band
    model_admin_class = BandAdmin

    @skip("Move this test to BulkEditJahrgang tests")
    @patch.object(ConfirmationViewMixin, 'get_context_data', return_value={})
    def test_get_context_data(self, _m):
        # get_context_data should add help text for the current step
        view = self.get_view()
        view.steps = Mock(current='1')
        context = view.get_context_data()
        self.assertNotIn('view_helptext', context)

        view.view_helptext = {
            '1': 'Step 1',
            '2': 'Step 2'
        }
        context = view.get_context_data()
        self.assertIn('view_helptext', context)
        self.assertEqual(context['view_helptext'], 'Step 1')
        view.steps = Mock(current='2')
        context = view.get_context_data()
        self.assertIn('view_helptext', context)
        self.assertEqual(context['view_helptext'], 'Step 2')

    def test_post_first_visit(self):
        """
        If there is no 'step' data in request.POST, post() should prepare the
        storage engine and render the first form.
        """
        view = self.get_view()
        request = self.post_request()
        with patch.multiple(view, storage=DEFAULT, steps=Mock(first='first step'), get_form=DEFAULT,
                            render=Mock(return_value='Rendered form.'), create=True):
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


@skip("Has not been reworked yet.")
class TestBulkEditJahrgang(ActionViewTestCase, LoggingTestMixin):
    view_class = BulkEditJahrgang
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [
        {  # obj1: jg + 0
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000, 2001],
            'e_datum': '2000-06-12', 'ausgabemonat__monat__ordinal': [6]
        },
        {  # obj2: jg + 1
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001],
            'e_datum': '2001-06-12', 'ausgabemonat__monat__ordinal': [6]
        },
        {  # obj3: ignored
            'magazin__magazin_name': 'Bad', 'jahrgang': 20, 'ausgabejahr__jahr': [2001]
        },
        {  # obj4: ignored?
            'magazin__magazin_name': 'Testmagazin'
        },
        {  # obj5: jg + 1
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2002],
            'e_datum': '2002-05-11', 'ausgabemonat__monat__ordinal': [5],
        },
        {  # obj6: jg + 2 when using e_datum, jg + 1 when using monat
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2002],
            'e_datum': '2002-06-12', 'ausgabemonat__monat__ordinal': [5]
        },
        {  # obj7: jg + 1
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001]
        },
        {  # obj8: jg + 2
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2002]
        },
    ]

    def setUp(self):
        super(TestBulkEditJahrgang, self).setUp()
        # noinspection PyUnresolvedReferences
        self.queryset = self.model.objects.exclude(pk=self.obj3.pk)

    def test_action_allowed(self):
        self.assertTrue(self.get_view().action_allowed)

        request = self.get_request()
        # Objects in this queryset have different magazines.
        queryset = self.model.objects.filter(ausgabejahr__jahr=2001)
        view = self.get_view(request, queryset=queryset)
        with patch.object(view.model_admin, 'message_user') as mocked_message:
            self.assertFalse(view.action_allowed)
            expected_message = (
                'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu'
                ' unterschiedlichen Magazinen.'
            )
            mocked_message.assert_called_once_with(
                request=request,
                message=expected_message,
                level=messages.ERROR
            )

    def test_compile_affected_objects(self):
        # result 0 0 => obj1
        # result 0 1 => obj1.affected_fields
        # result 1 0 => obj2
        # result 1 1 => obj2.affected_fields
        # affected_fields for this view: ['jahrgang','ausgabejahr__jahr']
        request = self.get_request()

        # noinspection PyUnresolvedReferences
        view = self.get_view(request, queryset=self.qs_obj1)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)

        view = self.get_view(request, queryset=self.queryset.order_by('pk'))
        result = view.compile_affected_objects()
        expected = ["Jahrgang: ---", "Jahr: 2000", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)
        expected = ["Jahrgang: ---", "Jahr: 2001"]
        self.assertEqual(result[1][1], expected)

        # noinspection PyUnresolvedReferences
        view = self.get_view(request, queryset=self.qs_obj3)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: 20", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)

    def test_post_action_not_allowed(self):
        # If the action is not allowed, post should REDIRECT us back to the changelist
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'bulk_jg',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj3.pk]
        }

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        expected_message = (
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu '
            'unterschiedlichen Magazinen.'
        )
        self.assertMessageSent(response.wsgi_request, expected_message)

    def test_post_show_confirmation_page(self):
        # get an ACTUAL response
        request = self.post_request()
        view = self.get_view(request)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        from django.template.response import TemplateResponse
        self.assertEqual(response.__class__, TemplateResponse)

    @tag('logging')
    def test_perform_action(self):
        request = self.get_request()
        view = self.get_view(request)
        # noinspection PyUnresolvedReferences
        view.perform_action({'jahrgang': 31416, 'start': self.obj1.pk})
        new_jg = (self.queryset
                  .values_list('jahrgang', flat=True)
                  .exclude(jahrgang=None)
                  .order_by('jahrgang')
                  .distinct())
        self.assertEqual(list(new_jg), [31416, 31417, 31418])
        for obj in self.queryset.all():
            self.assertLoggedChange(
                obj,
                change_message=[{"changed": {'fields': ['Jahrgang']}}]
            )

    @tag('logging')
    def test_perform_action_no_years(self):
        # obj4 has no years assigned, perform_action should assign it the
        # jahrgang value given by 'form_cleaned_data'.
        request = self.get_request()
        # noinspection PyUnresolvedReferences
        view = self.get_view(request, queryset=self.qs_obj4)
        # noinspection PyUnresolvedReferences
        form_cleaned_data = {'jahrgang': 31416, 'start': self.obj4.pk}
        view.perform_action(form_cleaned_data)
        # noinspection PyUnresolvedReferences
        new_jg = list(self.qs_obj4.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416])
        # noinspection PyUnresolvedReferences
        self.assertLoggedChange(
            self.obj4,
            change_message=[{"changed": {'fields': ['Jahrgang']}}]
        )

    @tag('logging')
    def test_perform_action_jahrgang_zero(self):
        request = self.get_request()
        view = self.get_view(request)
        # noinspection PyUnresolvedReferences
        view.perform_action({'jahrgang': 0, 'start': self.obj1.pk})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True).distinct())
        self.assertEqual(new_jg, [None])
        for obj in self.queryset.all():
            self.assertLoggedChange(
                obj,
                change_message=[{"changed": {'fields': ['Jahrgang']}}]
            )

    def test_permissions_required(self):
        # Assert that specific permissions are required to access this action.
        view = self.get_view()
        self.assertTrue(hasattr(view, 'allowed_permissions'))
        self.assertEqual(view.allowed_permissions, ['change'])


@skip("Has not been reworked yet.")
class TestMergeViewWizardedAusgabe(ActionViewTestCase):
    # Note that tests concerning logging for this view are done on
    # test_utils.merge_records directly.

    view_class = MergeViewWizarded
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [
        {'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000]},
        {'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001], 'jahrgang': 1},
        {'magazin__magazin_name': 'Bad', 'ausgabejahr__jahr': [2001], 'jahrgang': 20},
        {'magazin__magazin_name': 'Testmagazin', 'jahrgang': 2}
    ]

    def test_action_allowed(self):
        # noinspection PyUnresolvedReferences
        queryset = self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view = self.get_view(queryset=queryset)
        self.assertTrue(view.action_allowed)

    def test_action_allowed_low_qs_count(self):
        request = self.post_request()
        # noinspection PyUnresolvedReferences
        view = self.get_view(request=request, queryset=self.qs_obj1)
        self.assertFalse(view.action_allowed)
        expected_message = (
            'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden,'
            ' um diese Aktion durchzuführen.'
        )
        self.assertMessageSent(request, expected_message)

    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed)
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        self.assertMessageSent(request, expected_message)

    def test_post_action_not_allowed(self):
        # If the action is not allowed, post should REDIRECT us back to the changelist
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj3.pk]
        }

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        self.assertMessageSent(response.wsgi_request, expected_message)

    def test_post_first_visit(self):
        # post should return the first form (form_class: MergeFormSelectPrimary) of the Wizard
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name, 'admin/merge_records.html')
        self.assertIsInstance(
            response.context_data.get('form'), MergeFormSelectPrimary)
        self.assertIsInstance(
            response.context.get('wizard').get('form'), MergeFormSelectPrimary)

    def test_post_merge_conflict(self):
        # post should return the form that handles merge conflicts
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        # noinspection PyUnresolvedReferences
        form_data = {'0-primary': self.obj1.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data.get('form'), MergeConflictsFormSet)
        self.assertIsInstance(
            response.context.get('wizard').get('form'), MergeConflictsFormSet)

    def test_post_merge_conflict_success(self):
        # merge_conflicts have been resolved, post should REDIRECT
        # (through response_action) us back to the changelist

        # Step 0
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        # noinspection PyUnresolvedReferences
        form_data = {'0-primary': self.obj1.pk, '0-expand_primary': True}
        request_data.update(form_data)

        self.client.post(self.changelist_path, data=request_data)

        # Step 1
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {
            'merge_view_wizarded-current_step': 1,
            '1-INITIAL_FORMS': '0',
            '1-MAX_NUM_FORMS': '',
            '1-MIN_NUM_FORMS': '',
            '1-TOTAL_FORMS': '1',
        }
        request_data.update(management_form)
        form_data = {
            '1-0-verbose_fld_name': 'Jahrgang',
            '1-0-original_fld_name': 'jahrgang',
            '1-0-posvals': 0,
        }
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)

    def test_post_first_form_valid_and_no_merge_conflict(self):
        # post should return us back to the changelist
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        # noinspection PyUnresolvedReferences
        form_data = {'0-primary': self.obj1.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)

    def test_merge_not_updating_fields_it_should_not(self):
        # Check that the whole process does *NOT* change already present data
        # of the selected primary object.
        # spice up obj1 so we can verify that a merge has happened:
        # noinspection PyUnresolvedReferences
        self.qs_obj1.update(beschreibung='I really should not be here.')
        # noinspection PyUnresolvedReferences
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        # Select obj2 (or obj4) here as primary as it already has a value for
        # jahrgang (our only 'source' of conflict):
        # noinspection PyUnresolvedReferences
        form_data = {'0-primary': self.obj2.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)

        self.assertEqual(response.status_code, 302, msg="Redirect expected.")
        self.assertEqual(
            response.url, self.changelist_path,
            msg="Redirect back to changelist expected."
        )

        # noinspection PyUnresolvedReferences
        self.obj2.refresh_from_db()
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.obj2.jahrgang, 1)
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.obj2.beschreibung, 'I really should not be here.')

    @patch('dbentry.actions.views.get_updatable_fields', return_value=[])
    @patch.object(SessionWizardView, 'process_step', return_value={})
    def test_process_step(self, super_process_step, updatable_fields):
        view = self.get_view()
        view.get_form_prefix = mockv('0')
        view.storage = Mock(current_step='')
        last_step = MergeViewWizarded.CONFLICT_RESOLUTION_STEP
        view.steps = Mock(last=last_step)
        form = MergeFormSelectPrimary()

        # If expand_primary is False in MergeFormSelectPrimary, there cannot be
        # any conflicts and the last step should be up next.
        form.cleaned_data = {'expand_primary': False}
        self.assertEqual(view.process_step(form), {})
        self.assertEqual(view.storage.current_step, last_step)

        # If the 'primary' has no fields that can be updated, the returned dict
        # should not contain 'updates'.
        # noinspection PyUnresolvedReferences
        super_process_step.return_value = {'0-primary': self.obj1.pk}
        # noinspection PyUnresolvedReferences
        form.cleaned_data = {'0-primary': self.obj1.pk, 'expand_primary': True}
        # noinspection PyUnresolvedReferences
        self.assertEqual(view.process_step(form), {'0-primary': self.obj1.pk})

        # obj1 can be updated on the field 'jahrgang' with obj2's value
        updatable_fields.return_value = ['jahrgang']
        # noinspection PyUnresolvedReferences
        view.queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view.storage.current_step = ''
        processed_data = view.process_step(form)
        self.assertIn('updates', processed_data)
        self.assertIn('jahrgang', processed_data['updates'])
        self.assertEqual(processed_data['updates']['jahrgang'], ['1'])
        self.assertEqual(view.storage.current_step, last_step)

        # same as above, but with a conflict due to involving obj4 as well
        # noinspection PyUnresolvedReferences
        view.queryset = self.model.objects.filter(
            pk__in=[self.obj1.pk, self.obj2.pk, self.obj4.pk])
        view.storage.current_step = ''
        processed_data = view.process_step(form)
        self.assertIn('updates', processed_data)
        self.assertIn('jahrgang', processed_data['updates'])
        self.assertEqual(sorted(processed_data['updates']['jahrgang']), ['1', '2'])
        self.assertEqual(view.storage.current_step, '')

    @translation_override(language=None)
    @patch.object(WizardConfirmationView, 'get_context_data')
    def test_get_context_data_primary_step(self, super_get_context_data):
        # Assert that the context contains a 'cl' and 'primary_label' item.
        view = self.get_view()
        view.steps = Mock(current='0')
        super_get_context_data.return_value = {'form': MergeFormSelectPrimary()}
        with patch.object(view.model_admin, 'get_changelist_instance'):
            data = view.get_context_data()
            self.assertIn('cl', data)
            self.assertIn('primary_label', data)

    @patch.object(WizardView, 'get_form_kwargs', return_value={})
    def test_get_form_kwargs_select_primary(self, _super_get_form_kwargs):
        # noinspection PyUnresolvedReferences
        ids = [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        view = self.get_view(queryset=self.model.objects.filter(pk__in=ids))
        # MergeFormSelectPrimary step
        view.form_list = {MergeViewWizarded.SELECT_PRIMARY_STEP: MergeFormSelectPrimary}
        form_kwargs = view.get_form_kwargs(step='0')
        self.assertIn('choices', form_kwargs)
        formfield_name = '0-' + MergeFormSelectPrimary.PRIMARY_FIELD_NAME
        self.assertEqual(
            sorted(list(view.queryset.values_list('pk', flat=True))),
            sorted(list(form_kwargs['choices'][formfield_name].values_list('pk', flat=True)))
        )

    @patch.object(WizardView, 'get_form_kwargs', return_value={})
    def test_get_form_kwargs_conflicts(self, _super_get_form_kwargs):
        # noinspection PyUnresolvedReferences
        ids = [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        view = self.get_view(queryset=self.model.objects.filter(pk__in=ids))
        # MergeConflictsFormSet step
        view.form_list = {MergeViewWizarded.CONFLICT_RESOLUTION_STEP: MergeConflictsFormSet}
        view._updates = {'jahrgang': ['1', '2'], 'beschreibung': ['Test']}
        form_kwargs = view.get_form_kwargs(step='1')
        self.assertIn('data', form_kwargs)
        expected = {
            '1-TOTAL_FORMS': 1, '1-MAX_NUM_FORMS': '', '1-0-original_fld_name': 'jahrgang',
            '1-INITIAL_FORMS': '0', '1-0-verbose_fld_name': 'Jahrgang'
        }
        self.assertEqual(form_kwargs['data'], expected)
        self.assertIn('form_kwargs', form_kwargs)
        self.assertIn('choices', form_kwargs['form_kwargs'])
        self.assertEqual(
            form_kwargs['form_kwargs']['choices'], {'1-0-posvals': [(0, '1'), (1, '2')]})

    @translation_override(language=None)
    @patch.object(
        MergeViewWizarded,
        'perform_action',
        new=Mock(
            side_effect=models.deletion.ProtectedError('msg', _models.Artikel.objects.all()))
    )
    def test_done(self):
        # Assert that an admin message is send to user upon encountering a
        # ProtectedError during done.
        request = self.get_request()
        view = self.get_view(request=request)
        view.done()
        self.assertMessageSent(
            request, 'Folgende verwandte Artikel verhinderten die Zusammenführung:')

    def test_permissions_required(self):
        # Assert that specific permissions are required to access this action.
        view = self.get_view()
        self.assertTrue(hasattr(view, 'allowed_permissions'))
        self.assertEqual(view.allowed_permissions, ['merge'])

    @patch('dbentry.actions.views.merge_records')
    @patch.object(MergeViewWizarded, 'get_cleaned_data_for_step')
    def test_perform_action_no_expand(self, mocked_step_data, mocked_merge_records):
        # Assert that merge_records is called with the correct arguments.
        # Also check that no 'updates' are passed to merge_records if
        # expand_primary is False.
        # noinspection PyUnresolvedReferences
        step_data = {'primary': self.obj1.pk, 'expand_primary': False}
        mocked_step_data.return_value = step_data

        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        # Set the property's private attribute:
        view._updates = {'some_update': 'that_should not be used'}
        view.perform_action()
        self.assertTrue(mocked_merge_records.called)
        args, kwargs = mocked_merge_records.call_args
        # noinspection PyUnresolvedReferences
        self.assertEqual(
            args[0], self.obj1,
            msg="First argument to merge_records should be the primary model instance."
        )
        self.assertIsInstance(
            args[1], models.QuerySet,
            msg="Second argument should be the queryset."
        )
        self.assertFalse(
            args[2],
            msg="Third argument 'update_data' should be empty if "
                "expand_primary is False."
        )
        self.assertFalse(
            args[3],
            msg="Fourth argument 'expand' should be False."
        )


@skip("Has not been reworked yet.")
class TestMergeViewWizardedArtikel(ActionViewTestCase):
    view_class = MergeViewWizarded
    model = _models.Artikel
    model_admin_class = ArtikelAdmin
    test_data_count = 2

    def test_action_allowed_different_magazin(self):
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed)
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(request, expected_message)


@skip("Has not been reworked yet.")
class TestMoveToBrochureBase(ActionViewTestCase):
    view_class = MoveToBrochureBase
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin

    raw_data = [
        {
            'beschreibung': 'Testausgabe', 'bemerkungen': 'Testbemerkung',
            'sonderausgabe': True, 'bestand__extra': 1,
            'ausgabejahr__jahr': [2000, 2001],
            'magazin__magazin_name': 'Testmagazin', 'magazin__beschreibung': 'Beep boop'
        }
    ]

    def setUp(self):
        super().setUp()
        # noinspection PyUnresolvedReferences
        self.form_cleaned_data = [
            {
                'titel': 'Testausgabe', 'ausgabe_id': self.obj1.pk, 'accept': True,
            }
        ]
        # noinspection PyUnresolvedReferences
        self.mag = self.obj1.magazin

    @translation_override(language=None)
    def test_action_allowed_has_artikels(self):
        # noinspection PyUnresolvedReferences
        self.obj1.artikel_set.add(make(_models.Artikel, ausgabe=self.obj1))
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed)
        # noinspection PyUnresolvedReferences
        expected_message = (
            "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht "
            "verschoben werden können: {}"
        ).format(
            '<a href="/admin/dbentry/ausgabe/{}/change/">Testausgabe</a>'.format(
                str(self.obj1.pk)
            )
        )
        self.assertMessageSent(request, expected_message)

    @translation_override(language=None)
    def test_action_allowed_different_magazin(self):
        # Assert that only sets of a single magazin are allowed to be moved.
        make(self.model, magazin__magazin_name='The Other')
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.model.objects.all())
        self.assertFalse(view.action_allowed)
        expected_message = (
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu '
            'unterschiedlichen Magazinen.'
        )
        self.assertMessageSent(request, expected_message)

    def test_action_allowed(self):
        view = self.get_view(request=self.post_request(), queryset=self.queryset)
        self.assertTrue(view.action_allowed)

    def test_get_initial(self):
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        initial = view.get_initial()
        self.assertEqual(len(initial), 1)
        self.assertIn('ausgabe_id', initial[0])
        # noinspection PyUnresolvedReferences
        self.assertEqual(initial[0]['ausgabe_id'], self.obj1.pk)
        self.assertIn('titel', initial[0])
        # noinspection PyUnresolvedReferences
        self.assertEqual(initial[0]['titel'], self.obj1.magazin.magazin_name)
        self.assertIn('zusammenfassung', initial[0])
        # noinspection PyUnresolvedReferences
        self.assertEqual(initial[0]['zusammenfassung'], self.obj1.magazin.beschreibung)
        self.assertIn('beschreibung', initial[0])
        # noinspection PyUnresolvedReferences
        self.assertEqual(initial[0]['beschreibung'], self.obj1.beschreibung)
        self.assertIn('bemerkungen', initial[0])
        # noinspection PyUnresolvedReferences
        self.assertEqual(initial[0]['bemerkungen'], self.obj1.bemerkungen)

    def test_perform_action(self):
        # Assert that perform_action works correctly.

        # 'zusammenfassung' should make it into the new record:
        self.form_cleaned_data[0]['zusammenfassung'] = 'Bleep bloop'
        # 'beschreibung' with an empty value, should NOT make it into the new record:
        self.form_cleaned_data[0]['beschreibung'] = ''
        options_form_cleaned_data = {'brochure_art': 'brochure'}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        # noinspection PyUnresolvedReferences
        changed_bestand = self.obj1.bestand_set.first()
        self.assertEqual(_models.Brochure.objects.count(), 0)
        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertEqual(_models.Brochure.objects.count(), 1)
        new_brochure = _models.Brochure.objects.get()

        # Inspect the brochure attributes
        self.assertEqual(new_brochure.titel, 'Testausgabe')
        self.assertEqual(new_brochure.zusammenfassung, 'Bleep bloop')
        self.assertFalse(new_brochure.beschreibung)
        # Inspect the bestand
        changed_bestand.refresh_from_db()
        self.assertEqual(new_brochure.bestand_set.first(), changed_bestand)
        self.assertIsNone(changed_bestand.ausgabe_id)
        # Assert that the primary was deleted
        # noinspection PyUnresolvedReferences
        self.assertFalse(self.model.objects.filter(pk=self.obj1.pk).exists())

    def test_perform_action_deletes_magazin(self):
        options_form_cleaned_data = {'brochure_art': 'brochure', 'delete_magazin': True}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertFalse(_models.Magazin.objects.filter(pk=self.mag.pk).exists())

    def test_perform_action_not_deletes_magazin(self):
        options_form_cleaned_data = {'brochure_art': 'brochure', 'delete_magazin': False}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertTrue(_models.Magazin.objects.filter(pk=self.mag.pk).exists())

    def test_perform_action_moves_jahre(self):
        options_form_cleaned_data = {'brochure_art': 'brochure'}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag
        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        new_brochure = _models.Brochure.objects.get()
        self.assertEqual(
            list(new_brochure.jahre.values_list('jahr', flat=True)), [2000, 2001])

    def test_perform_action_adds_hint_to_changelog(self):
        options_form_cleaned_data = {'brochure_art': 'brochure'}
        expected = (
            "Hinweis: {verbose_name} wurde automatisch erstellt beim "
            "Verschieben von Ausgabe {str_ausgabe} (Magazin: {str_magazin})."
        )
        # noinspection PyUnresolvedReferences
        expected = expected.format(
            verbose_name=_models.Brochure._meta.verbose_name,
            str_ausgabe=str(self.obj1), str_magazin=str(self.obj1.magazin)
        )
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view._magazin_instance = self.mag
        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        new_brochure = _models.Brochure.objects.get()
        ct = ContentType.objects.get_for_model(_models.Brochure)
        logentry = LogEntry.objects.get(object_id=new_brochure.pk, content_type=ct)
        self.assertEqual(logentry.get_change_message(), expected)

    def test_perform_action_katalog(self):
        options_form_cleaned_data = {'brochure_art': 'katalog'}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        self.assertEqual(_models.Katalog.objects.count(), 0)
        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertEqual(_models.Katalog.objects.count(), 1)
        self.assertEqual(_models.Katalog.objects.get().art, _models.Katalog.Types.MERCH)

    def test_perform_action_kalender(self):
        options_form_cleaned_data = {'brochure_art': 'kalender'}
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        self.assertEqual(_models.Kalender.objects.count(), 0)
        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertEqual(_models.Kalender.objects.count(), 1)

    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_protected_ausgabe(self, mocked_model_from_string):
        mocked_model_from_string.return_value = _models.Brochure
        options_form_cleaned_data = {'brochure_art': 'brochure'}

        # noinspection PyUnresolvedReferences
        self.obj1.artikel_set.add(make(_models.Artikel, ausgabe_id=self.obj1.pk))
        request = self.get_request()
        view = self.get_view(request=request, queryset=self.queryset)
        view.mag = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        # noinspection PyUnresolvedReferences
        self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
        # noinspection PyUnresolvedReferences
        expected_message = (
            'Folgende Ausgaben konnten nicht gelöscht werden: '
            '<a href="/admin/dbentry/ausgabe/{pk}/change/" target="_blank">{name}</a> '
            '(<a href="/admin/dbentry/ausgabe/?id__in={pk}" target="_blank">Liste</a>). '
            'Es wurden keine Broschüren für diese Ausgaben erstellt.'
        ).format(pk=self.obj1.pk, name=str(self.obj1))
        self.assertMessageSent(request, expected_message)

        # No new brochure objects should have been created
        self.assertEqual(_models.Brochure.objects.count(), 0)

    @patch('dbentry.actions.views.is_protected')
    @patch('dbentry.actions.views.get_model_from_string')
    def test_perform_action_does_not_roll_back_ausgabe_deletion(
            self, mocked_model_from_string, mocked_is_protected):
        # Assert that a rollback on trying to delete the magazin does not also
        # roll back the ausgabe.
        mocked_model_from_string.return_value = _models.Brochure
        mocked_is_protected.return_value = False
        options_form_cleaned_data = {'brochure_art': 'brochure', 'delete_magazin': True}

        # noinspection PyUnresolvedReferences
        ausgabe_id = self.obj1.pk
        # noinspection PyUnresolvedReferences
        magazin_id = self.obj1.magazin_id
        # Create an ausgabe that will force a ProtectedError:
        make(self.model, magazin_id=magazin_id)
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertFalse(self.model.objects.filter(pk=ausgabe_id).exists())
        self.assertTrue(_models.Magazin.objects.filter(pk=magazin_id).exists())

    def test_perform_action_not_accepted(self):
        # Assert that an ausgabe is not changed if the user unticks 'accept'.
        options_form_cleaned_data = {'brochure_art': 'brochure'}
        # noinspection PyUnresolvedReferences
        ausgabe_id = self.obj1.pk
        self.form_cleaned_data[0]['accept'] = False
        view = self.get_view(request=self.get_request(), queryset=self.queryset)
        view.mag = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertTrue(self.model.objects.filter(pk=ausgabe_id).exists())
        self.assertEqual(_models.BaseBrochure.objects.count(), 0)

    def test_context_contains_options_form(self):
        view = self.get_view(self.get_request())
        context = view.get_context_data()
        self.assertIn('options_form', context)

        self.assertIsInstance(context['options_form'], BrochureActionFormOptions)

    @patch(
        'dbentry.actions.views.MoveToBrochureBase.can_delete_magazin',
        new_callable=PropertyMock
    )
    def test_conditionally_show_delete_magazin_option(self, mocked_can_delete):
        # Assert that the field 'delete_magazin' only shows up on the options_form
        # if the magazin can be deleted.

        # Can be deleted:
        mocked_can_delete.return_value = True
        form = self.get_view(self.get_request()).get_options_form()
        self.assertIn('delete_magazin', form.fields)

        # Cannot be deleted:
        mocked_can_delete.return_value = False
        form = self.get_view(self.get_request()).get_options_form()
        self.assertNotIn('delete_magazin', form.fields)

    def test_can_delete_magazin(self):
        # Assert that can_delete_magazin returns True when the magazin can be
        # deleted after the action.
        view = self.get_view(self.get_request())
        # noinspection PyUnresolvedReferences
        view._magazin_instance = self.obj1.magazin
        self.assertTrue(view.can_delete_magazin)

        # Add another ausgabe to magazin to forbid the deletion of it.
        # noinspection PyUnresolvedReferences
        make(self.model, magazin=self.obj1.magazin)
        # noinspection PyUnresolvedReferences
        view = self.get_view(
            self.get_request(), queryset=self.model.objects.filter(pk=self.obj1.pk))
        # noinspection PyUnresolvedReferences
        view._magazin_instance = self.obj1.magazin
        self.assertFalse(view.can_delete_magazin)

        view = self.get_view(self.get_request())
        view._magazin_instance = None
        self.assertFalse(
            view.can_delete_magazin,
            msg="Should return False if can_delete_magazin is called with no "
                "'magazin_instance' set."
        )

    def test_permissions_required(self):
        # Assert that specific permissions are required to access this action.
        view = self.get_view()
        self.assertTrue(hasattr(view, 'allowed_permissions'))
        self.assertEqual(view.allowed_permissions, ['moveto_brochure'])

    def test_story(self):
        other_mag = make(_models.Magazin)
        other = make(self.model, magazin=other_mag)
        management_form_data = {
            'form-TOTAL_FORMS': '2', 'form-INITIAL_FORMS': '0', 'form-MAX_NUM_FORMS': ''
        }

        # User selects two ausgaben of different magazines and gets a message about it
        # noinspection PyUnresolvedReferences
        changelist_post_data = {
            'action': ['moveto_brochure'],
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, other.pk]
        }
        response = self.client.post(path=self.changelist_path, data=changelist_post_data)
        self.assertEqual(
            response.status_code, 302,
            msg="Failed action. Should be a redirect back to the changelist.")
        expected_message = (
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu '
            'unterschiedlichen Magazinen.'
        )
        self.assertMessageSent(response.wsgi_request, expected_message)

        # User selects a single ausgabe and proceeds to the selection
        # noinspection PyUnresolvedReferences
        changelist_post_data[helpers.ACTION_CHECKBOX_NAME] = [self.obj1.pk]
        response = self.client.post(path=self.changelist_path, data=changelist_post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.view_class.template_name, [t.name for t in response.templates],
            msg="Should be rendering the MoveToBrochure template."
        )

        # User aborts and is directed back to the changelist
        response = self.client.get(path=self.changelist_path)
        self.assertEqual(response.status_code, 200)

        # User selects another valid ausgabe and returns to the selection with
        # the two instances.
        obj2 = make(self.model, magazin=self.mag)
        # noinspection PyUnresolvedReferences
        changelist_post_data[helpers.ACTION_CHECKBOX_NAME] = [self.obj1.pk, obj2.pk]
        response = self.client.post(path=self.changelist_path, data=changelist_post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.view_class.template_name, [t.name for t in response.templates],
            msg="Should be rendering the MoveToBrochure template."
        )

        # User selects the 'Katalog' category and confirms, without having
        # checked the delete_magazin checkbox.
        # noinspection PyUnresolvedReferences
        post_data = {
            'action_confirmed': 'Ja, ich bin sicher',
            'brochure_art': 'katalog',
            'delete_magazin': False,
            'form-0-titel': 'Whatever',
            'form-0-ausgabe_id': self.obj1.pk,
            'form-0-accept': True,
            'form-1-titel': 'Whatever2',
            'form-1-ausgabe_id': obj2.pk,
            'form-1-accept': True,
        }
        post_data.update(changelist_post_data)
        post_data.update(management_form_data)
        response = self.client.post(path=self.changelist_path, data=post_data)
        self.assertTrue(_models.Magazin.objects.filter(pk=self.mag.pk).exists())

        # User is redirected back to the changelist
        self.assertEqual(response.status_code, 302)

        # User selects another ausgabe and this time also deletes the magazin
        changelist_post_data[helpers.ACTION_CHECKBOX_NAME] = [other.pk]
        response = self.client.post(path=self.changelist_path, data=changelist_post_data)
        self.assertEqual(response.status_code, 200)
        management_form_data['form-TOTAL_FORMS'] = '1'
        post_data = {
            'action_confirmed': 'Ja, ich bin sicher',
            'brochure_art': 'katalog',
            'delete_magazin': True,
            'form-0-titel': 'Whatever',
            'form-0-ausgabe_id': other.pk,
            'form-0-accept': True,
        }
        post_data.update(changelist_post_data)
        post_data.update(management_form_data)
        response = self.client.post(path=self.changelist_path, data=post_data)
        self.assertFalse(_models.Magazin.objects.filter(pk=other_mag.pk).exists())

        # User is redirected back to the changelist
        self.assertEqual(response.status_code, 302)


@skip("Has not been reworked yet.")
class TestChangeBestand(ActionViewTestCase, LoggingTestMixin):
    view_class = ChangeBestand
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin
    action_name = 'change_bestand'

    @classmethod
    def setUpTestData(cls):
        cls.lagerort1 = make(_models.Lagerort)
        cls.lagerort2 = make(_models.Lagerort)
        mag = make(_models.Magazin, magazin_name='Testmagazin')

        cls.obj1 = make(cls.model, magazin=mag)
        super().setUpTestData()

    def get_request_data(self, **kwargs):
        return {
            'action': 'change_bestand',
            helpers.ACTION_CHECKBOX_NAME: '%s' % self.obj1.pk,
            **kwargs
        }

    @staticmethod
    def get_form_data(parent_obj, *bestand_objects):
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
            form_data.update({
                form_prefix + '-ausgabe': parent_obj.pk,
                form_prefix + '-signatur': bestand_obj_pk or '',
                form_prefix + '-lagerort': lagerort_pk or ''
            })
        return {**management_form_data, **form_data}

    def test_success_add(self):
        # Assert that Bestand instances are added to obj1's bestand_set.
        response = self.client.post(
            path=self.changelist_path,
            data={
                **self.get_request_data(action_confirmed='Yes'),
                **self.get_form_data(self.obj1, (None, self.lagerort1.pk))
            },
            follow=False
        )
        self.assertEqual(
            response.status_code, 302,
            msg="Expected a redirect back to the changelist."
        )
        self.assertEqual(self.obj1.bestand_set.count(), 1)
        b = self.obj1.bestand_set.get()
        self.assertEqual(b.lagerort, self.lagerort1)

    def test_success_update(self):
        # Assert that Bestand instances in obj1's bestand_set can be updated.
        b = _models.Bestand(lagerort=self.lagerort1, ausgabe=self.obj1)
        b.save()
        response = self.client.post(
            path=self.changelist_path,
            data={
                **self.get_request_data(action_confirmed='Yes'),
                **self.get_form_data(self.obj1, (b.pk, self.lagerort2.pk))
            },
            follow=False
        )
        self.assertEqual(
            response.status_code, 302,
            msg="Expected a redirect back to the changelist."
        )
        self.assertEqual(self.obj1.bestand_set.count(), 1)
        new_bestand = self.obj1.bestand_set.get()
        self.assertEqual(new_bestand.lagerort, self.lagerort2)

    def test_success_delete(self):
        # Test that Bestand relations can be deleted:
        b = _models.Bestand(lagerort=self.lagerort1, ausgabe=self.obj1)
        b.save()
        form_data = self.get_form_data(self.obj1, (b.pk, self.lagerort1.pk))
        form_data['bestand_set-%s-0-DELETE' % self.obj1.pk] = True
        response = self.client.post(
            path=self.changelist_path,
            data={
                **self.get_request_data(action_confirmed='Yes'),
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
        # A post request with invalid formsets should not post successfully,
        # i.e. not return back to the changelist.
        # Two formsets, of which the second has an invalid lagerort:
        form_data = self.get_form_data(
            self.obj1, (None, self.lagerort1.pk), (None, -1))
        response = self.client.post(
            path=self.changelist_path,
            data={**self.get_request_data(action_confirmed='Yes'), **form_data},
            follow=False
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.view_class.template_name)

    def test_get_bestand_formset(self):
        # Check that get_bestand_formset returns the expected formset & inline.
        self.obj1.bestand_set.create(lagerort=self.lagerort1)
        request = self.post_request(
            path=self.changelist_path,
            data=self.get_request_data()
        )
        view = self.get_view(request)
        formset, inline = view.get_bestand_formset(request, self.obj1)
        # Check some attributes of the formset/inline.
        self.assertEqual(inline.model, _models.Bestand)
        self.assertEqual(formset.instance, self.obj1)
        self.assertEqual(list(formset.queryset.all()), list(self.obj1.bestand_set.all()))

    def test_get_bestand_formset_form_data(self):
        # Assert that get_bestand_formset only adds formset data if the
        # submit keyword ('action_confirmed') is present in the request.
        request = self.post_request(
            path=self.changelist_path,
            data=self.get_request_data()
        )
        view = self.get_view(request)
        formset, inline = view.get_bestand_formset(request, self.obj1)
        self.assertFalse(formset.data)
        request = self.post_request(
            path=self.changelist_path,
            data={
                **self.get_request_data(action_confirmed='Yes'),
                **self.get_form_data(self.obj1, (None, self.lagerort1.pk))
            }
        )
        view = self.get_view(request)
        formset, inline = view.get_bestand_formset(request, self.obj1)
        self.assertTrue(formset.data)

    def test_media(self):
        # Assert that the formset's media is added to the context.
        other = make(self.model)
        response = self.client.post(
            path=self.changelist_path,
            data=self.get_request_data(**{
                # Use a queryset with two objects to check the coverage on that
                # 'media_updated condition'.
                helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, other.pk]
            }),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('media', response.context)
        from django.conf import settings
        self.assertIn(
            'admin/js/inlines.js',
            response.context['media']._js
        )

    def test_get_bestand_formset_no_inline(self):
        # get_bestand_formset should throw an error when attempting to get the
        # Bestand inline for a model_admin_class that doesn't have such an
        # inline.
        mocked_inlines = Mock(return_value=[])
        with patch.object(self.model_admin, 'get_formsets_with_inlines', new=mocked_inlines):
            with self.assertRaises(ValueError):
                request = self.get_request()
                view = self.get_view(request=request)
                view.get_bestand_formset(request, None)
