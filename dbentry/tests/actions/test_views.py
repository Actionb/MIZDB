from unittest.mock import patch, Mock, PropertyMock

from formtools.wizard.views import SessionWizardView, WizardView

from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import tag
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
from dbentry.base.views import MIZAdminMixin, FixedSessionWizardView
from dbentry.factory import make
from dbentry.sites import miz_site
from dbentry.tests.actions.base import ActionViewTestCase
from dbentry.tests.base import AdminTestCase, mockv
from dbentry.tests.mixins import LoggingTestMixin
from dbentry.utils import get_obj_link  # parameters: obj, user, admin_site


class TestConfirmationViewMixin(AdminTestCase):
    model = _models.Audio
    model_admin_class = AudioAdmin

    def get_instance(self, **kwargs):
        initkwargs = dict(model_admin=self.model_admin, queryset=self.model.objects.all())
        initkwargs.update(kwargs)
        return ConfirmationViewMixin(**initkwargs)

    def test_init_sets_action_name(self):
        ConfirmationViewMixin.action_name = 'test'
        instance = self.get_instance()
        self.assertEqual(instance.action_name, 'test')

        # init should set action_name if the class does not have that attribute
        ConfirmationViewMixin.action_name = None
        instance = self.get_instance()
        self.assertTrue(hasattr(instance, 'action_name'))
        self.assertEqual(instance.action_name, instance.__class__.__name__)

    def test_perform_action_not_implemented(self):
        # this base class has not implemented the perform_action method
        instance = self.get_instance()
        with self.assertRaises(NotImplementedError):
            instance.perform_action(form_cleaned_data={})

    def test_dispatch_action_not_allowed(self):
        # dispatch should redirect 'back' (here: return None) if the action is not allowed
        instance = self.get_instance()
        instance._action_allowed = False
        self.assertIsNone(instance.dispatch(self.get_request()))

    # noinspection SpellCheckingInspection
    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data', return_value={})
    def test_get_context_data(self, _mocked_super_get_context_data):
        instance = self.get_instance()
        instance.title = 'Mergeaudio'
        instance.breadcrumbs_title = 'Breads'

        context = instance.get_context_data()
        self.assertEqual(context.get('title'), 'Mergeaudio')
        self.assertEqual(context.get('breadcrumbs_title'), 'Breads')
        self.assertEqual(
            context.get('non_reversible_warning'), instance.non_reversible_warning)

    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data', return_value={})
    def test_get_context_data_object_name_singular(self, _mocked_super_get_context_data):
        # Assert that the context_data 'objects_name' is the singular of the
        # verbose_name when the queryset contains exactly one object.
        instance = self.get_instance()
        instance.queryset = Mock(count=Mock(return_value=1))
        context = instance.get_context_data()
        self.assertEqual(
            context.get('objects_name'), instance.opts.verbose_name,
            msg="Expected objects_name to be the singular verbose_name."
        )

    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data', return_value={})
    def test_get_context_data_object_name_plural(self, _mocked_super_get_context_data):
        # Assert that the context_data 'objects_name' is the plural of the
        # verbose_name when the queryset contains no or more than one object.
        instance = self.get_instance()
        c1 = instance.get_context_data()
        instance.queryset = Mock(count=Mock(return_value=2))
        c2 = instance.get_context_data()
        for desc, context in (('no objects', c1), ('multiple objects', c2)):
            with self.subTest(desc):
                self.assertEqual(
                    context.get('objects_name'), instance.opts.verbose_name_plural)


class TestActionConfirmationView(ActionViewTestCase):
    view_class = ActionConfirmationView
    model = _models.Band
    model_admin_class = BandAdmin
    test_data_count = 1

    def test_compile_affected_objects(self):
        request = self.get_request()
        view = self.get_view(request=request)
        # noinspection PyUnresolvedReferences
        expected = [('Band: ' + get_obj_link(self.obj1, request.user, blank=True), )]
        self.assertEqual(view.compile_affected_objects(), expected)

        # noinspection PyUnresolvedReferences
        a = make(_models.Audio, band=self.obj1, genre__extra=2)
        view = self.get_view(
            request,
            model_admin=AudioAdmin(_models.Audio, miz_site),
            queryset=_models.Audio.objects.all()
        )
        view.affected_fields = [
            'titel', 'band__band_name', 'genre__genre', 'release_id']
        link_list = view.compile_affected_objects()
        # link_list should have a structure like this:
        # [
        #       ('Audio Material: <link of obj1>', [<affected objects>]),
        #       ('Audio Material: <link of obj2>', [<affected objects>]),
        #       ...
        # ]
        # In this case here, the list only has one object (first index==0).
        expected = 'Audio Material: ' + get_obj_link(a, request.user, blank=True)
        self.assertEqual(
            link_list[0][0], expected,
            msg="First item should be the link to the audio object."
        )
        # Evaluating the list of 'affected objects'. This list is determined by
        # view.affected_fields.
        # First item should just be the titel of 'a'.
        self.assertEqual(link_list[0][1][0], 'Titel: ' + a.titel)
        # Second item should a link to the band object:
        expected = 'Band: ' + get_obj_link(a.band.first(), request.user, blank=True)
        self.assertEqual(link_list[0][1][1], expected)
        # The next two items should be links to the Genre objects:
        genres = a.genre.all().order_by('genre')
        expected = 'Genre: ' + get_obj_link(genres[0], request.user, blank=True)
        self.assertEqual(link_list[0][1][2], expected)
        expected = 'Genre: ' + get_obj_link(genres[1], request.user, blank=True)
        self.assertEqual(link_list[0][1][3], expected)
        # And the last item should be the release_id:
        self.assertEqual(link_list[0][1][4], 'Release ID (discogs): ---')

    def test_compile_affected_objects_choices(self):
        # Assert that for fields with choices the human readable part is displayed.
        obj = make(_models.Ausgabe, status=_models.Ausgabe.INBEARBEITUNG)
        view = self.get_view(
            request=self.get_request(),
            model_admin=AusgabenAdmin(_models.Ausgabe, miz_site),
            queryset=_models.Ausgabe.objects.filter(pk=obj.pk)
        )
        view.affected_fields = ['status']
        status_field = _models.Ausgabe._meta.get_field('status')
        expected = "%s: %s" % (  # "Bearbeitungsstatus: in Bearbeitung"
            status_field.verbose_name,
            dict(status_field.choices)[_models.Ausgabe.INBEARBEITUNG]
        )
        self.assertEqual(view.compile_affected_objects()[0][1][0], expected)

    def test_form_valid(self):
        # form_valid should redirect back to the changelist
        # a return value of None will make options.ModelAdmin.response_action redirect there
        view = self.get_view()
        view.perform_action = Mock()
        self.assertIsNone(view.form_valid(Mock()))


class TestWizardConfirmationView(ActionViewTestCase):
    view_class = WizardConfirmationView
    model = _models.Audio
    model_admin_class = AudioAdmin

    @patch.object(ConfirmationViewMixin, 'get_context_data', return_value={})
    def test_get_context_data(self, _m):
        # get_context_data should add helptext for the current step
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

    @patch.object(SessionWizardView, 'post', return_value='WizardForm!')
    @patch.object(FixedSessionWizardView, '__init__')
    def test_post(self, _x, _y):
        # If there is no 'step' data in request.POST, post() should return the
        # rendered first form of the wizard.
        request = self.post_request()
        view = self.get_view(request)
        view.storage = Mock()
        view.steps = Mock(first='1')
        view.get_form = mockv('The first form!')
        view.render = mockv('Rendered form.')
        self.assertEqual(view.post(request), 'Rendered form.')
        self.assertEqual(view.storage.reset.call_count, 1)
        self.assertEqual(view.render.call_count, 1)
        view.storage.current_step = '1'

        # SessionWizardView -> WizardView -> normalize_name
        prefix = 'wizard_confirmation_view'
        request = self.post_request(data={prefix + '-current_step': '2'})
        self.assertEqual(view.post(request), 'WizardForm!')


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
            response.templates[0].name, 'admin/action_confirmation_wizard.html')
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
    @patch.object(WizardConfirmationView, 'get_context_data', return_value={})
    def test_get_context_data(self, _super_get_context_data):
        # Assert that 'title' is counting up with 'step'
        view = self.get_view()
        view.steps = Mock(current='0')
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 1')
        view.steps.current = '22'
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 23')

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

        view = self.get_view(queryset=self.queryset)
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
        self.assertEqual(_models.Katalog.objects.get().art, 'merch')

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
            'admin/js/inlines%s.js' % ('' if settings.DEBUG else '.min'),
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
