from unittest.mock import patch, Mock, PropertyMock

from formtools.wizard.views import SessionWizardView, WizardView

from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import tag
from django.utils.translation import override as translation_override
from django.utils.safestring import SafeText
from django.urls import reverse

import DBentry.models as _models
from DBentry.admin import BandAdmin, AusgabenAdmin, ArtikelAdmin, AudioAdmin
from DBentry.actions.base import (
    ActionConfirmationView, ConfirmationViewMixin, WizardConfirmationView)
from DBentry.actions.views import (
    BulkEditJahrgang, BulkAddBestand, MergeViewWizarded, MoveToBrochureBase)
from DBentry.actions.forms import (
    MergeConflictsFormSet, MergeFormSelectPrimary, BrochureActionFormOptions)
from DBentry.base.views import MIZAdminMixin, FixedSessionWizardView
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.factory import make
from DBentry.sites import miz_site
from DBentry.tests.actions.base import ActionViewTestCase
from DBentry.tests.base import AdminTestCase, mockv
from DBentry.tests.mixins import LoggingTestMixin
from DBentry.utils import get_obj_link  # parameters: obj, user, admin_site


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
            instance.perform_action()

    def test_dispatch_action_not_allowed(self):
        # dispatch should redirect 'back' (here: return None) if the action is not allowed
        instance = self.get_instance()
        instance._action_allowed = False
        self.assertIsNone(instance.dispatch(self.get_request()))

    @translation_override(language=None)
    @patch.object(MIZAdminMixin, 'get_context_data', return_value={})
    def test_get_context_data(self, mocked_super_get_context_data):
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
    def test_get_context_data_object_name_singular(self, mocked_super_get_context_data):
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
    def test_get_context_data_object_name_plural(self, mocked_super_get_context_data):
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
        expected = [['Band: '+ get_obj_link(self.obj1, request.user, blank=True)]]
        self.assertEqual(view.compile_affected_objects(), expected)

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
        #       ['Audio Material: <link of obj1>', [<affected objects>]],
        #       ['Audio Material: <link of obj2>', [<affected objects>]],
        #       ...
        # ]
        # In this case here, the list only has one object (first index==0).
        expected = 'Audio Material: '+ get_obj_link(a, request.user, blank=True)
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
        expected = 'Genre: '+ get_obj_link(genres[1], request.user, blank=True)
        self.assertEqual(link_list[0][1][3], expected)
        # And the last item should be the release_id:
        self.assertEqual(link_list[0][1][4], 'Release ID (discogs): ---')

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
    def test_get_context_data(self, m):
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
    def test_post(self, x, y):
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
        self.queryset = self.model.objects.exclude(pk=self.obj3.pk)

    def test_action_allowed(self):
        self.assertTrue(self.get_view().action_allowed)

        request = self.get_request()
        # Objects in this queryset have different magazines.
        queryset = self.model.objects.filter(ausgabejahr__jahr=2001)
        view = self.get_view(request, queryset=queryset)
        view.model_admin.message_user = Mock()
        self.assertFalse(view.action_allowed)

        expected_message = (
            'Aktion abgebrochen: Die ausgewählten Ausgaben gehören zu'
            ' unterschiedlichen Magazinen.'
        )
        view.model_admin.message_user.assert_called_once_with(
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

        view = self.get_view(request, queryset=self.qs_obj3)
        result = view.compile_affected_objects()
        expected = ["Jahrgang: 20", "Jahr: 2001"]
        self.assertEqual(result[0][1], expected)

    def test_post_action_not_allowed(self):
        # If the action is not allowed, post should REDIRECT us back to the changelist
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
        view.perform_action({'jahrgang': 31416, 'start': self.obj1.pk})
        new_jg = (self.queryset
            .values_list('jahrgang', flat=True)
            .exclude(jahrgang=None)
            .order_by('jahrgang')
            .distinct())
        self.assertEqual(list(new_jg), [31416, 31417, 31418])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')

    @tag('logging')
    def test_perform_action_no_years(self):
        # obj4 has no years assigned, perform_action should assign it the
        # jahrgang value given by 'form_cleaned_data'.
        request = self.get_request()
        view = self.get_view(request, queryset=self.qs_obj4)
        form_cleaned_data = {'jahrgang': 31416, 'start': self.obj4.pk}
        view.perform_action(form_cleaned_data)
        new_jg = list(self.qs_obj4.values_list('jahrgang', flat=True))
        self.assertEqual(new_jg, [31416])
        self.assertLoggedChange(self.obj4, 'jahrgang')

    @tag('logging')
    def test_perform_action_jahrgang_zero(self):
        request = self.get_request()
        view = self.get_view(request)
        view.perform_action({'jahrgang': 0, 'start': self.obj1.pk})
        new_jg = list(self.queryset.values_list('jahrgang', flat=True).distinct())
        self.assertEqual(new_jg, [None])
        for obj in self.queryset.all():
            self.assertLoggedChange(obj, 'jahrgang')

    def test_permissions_required(self):
        # Assert that specific permissions are required to access this action.
        view = self.get_view()
        self.assertTrue(hasattr(view, 'allowed_permissions'))
        self.assertEqual(view.allowed_permissions, ['change'])


class TestBulkAddBestand(ActionViewTestCase, LoggingTestMixin):

    view_class = BulkAddBestand
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        cls.bestand_lagerort = make(_models.Lagerort, pk=ZRAUM_ID, ort='Bestand')
        cls.dubletten_lagerort = make(_models.Lagerort, pk=DUPLETTEN_ID, ort='Dublette')
        mag = make(_models.Magazin, magazin_name='Testmagazin')

        cls.obj1 = make(cls.model, magazin=mag)
        cls.obj2 = make(cls.model, magazin=mag, bestand__lagerort=cls.bestand_lagerort)
        cls.obj3 = make(cls.model, magazin=mag, bestand__lagerort=cls.dubletten_lagerort)
        cls.obj4 = make(
            cls.model, magazin=mag,
            bestand__lagerort=[cls.bestand_lagerort, cls.dubletten_lagerort]
        )

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        super().setUpTestData()

    def test_compile_affected_objects(self):
        # Assert that links to the instance's bestand objects are included.
        def get_bestand_links(obj):
            view_name = "admin:DBentry_%s_change" % (_models.Bestand._meta.model_name)
            link_template = '<a href="{url}" target="_blank">{lagerort__ort}</a>'
            template = 'Bestand: {link}'
            for pk, lagerort__ort in obj.bestand_set.values_list('pk', 'lagerort__ort'):
                url = reverse(view_name, args=[pk])
                link = link_template.format(url=url, lagerort__ort=lagerort__ort)
                yield template.format(link=link)

        request = self.get_request()
        # We are expecting the link_list to be ordered according to the order
        # in which we created the test objects; order by 'pk'.
        view = self.get_view(request, queryset=self.queryset.order_by('pk'))
        link_list = view.compile_affected_objects()
        self.assertEqual(len(link_list), 4)
        expected = [
            # obj1 has no bestand, no links expected
            [],
        ]
        # Let the helper function add the expected links for the other objects.
        expected.extend(
            get_bestand_links(obj)
            for obj in self.test_data[1:]
        )

        for i, links in enumerate(expected):
            # The first item of every link_list is the link to the main object.
            # The second is the sub list of affected objects.
            with self.subTest(i=i, obj="obj%s" % (i + 1)):
                if not links:
                    self.assertFalse(
                        link_list[i][1],  msg="No bestand links expected."
                    )
                for j, link in enumerate(links, 1):
                    with self.subTest(link_number=str(j)):
                        self.assertIn(link, link_list[i][1])

    @patch("DBentry.actions.views.link_list")
    def test_build_message(self, mocked_link_list):
        # Assert that build_message creates a SafeText string.
        mocked_link_list.return_value = "Beep, Boop"
        mocked_fkey = Mock()
        mocked_fkey.name = "whatever"
        message = self.get_view()._build_message(
            lagerort_instance="Attic",
            bestand_instances=[Mock(), Mock()],
            fkey=mocked_fkey,  # passed to mocked_link_list
        )
        self.assertIsInstance(message, SafeText)
        self.assertEqual(
            message,
            "Attic-Bestand zu diesen 2 Ausgaben hinzugefügt: Beep, Boop"
        )

    @tag('logging')
    def test_perform_action(self):
        # Record the bestand of the objects before the action
        old_bestand1 = list(self.obj1.bestand_set.values_list('pk', flat=True))
        old_bestand2 = list(self.obj2.bestand_set.values_list('pk', flat=True))
        old_bestand3 = list(self.obj3.bestand_set.values_list('pk', flat=True))
        old_bestand4 = list(self.obj4.bestand_set.values_list('pk', flat=True))

        request = self.get_request()
        view = self.get_view(request=request)
        view.perform_action(
            {'bestand': self.bestand_lagerort, 'dublette': self.dubletten_lagerort})

        # obj1 has no bestand at all; this should add a 'bestand' bestand (hurrr)
        all_bestand = list(self.obj1.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj1.bestand_set.exclude(pk__in=old_bestand1)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj1, new_bestand.first())

        # obj2 has one 'bestand' bestand; this should add a dublette
        all_bestand = list(self.obj2.bestand_set.values_list('lagerort', flat=True))
        expected = [self.bestand_lagerort.pk, self.dubletten_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj2.bestand_set.exclude(pk__in=old_bestand2)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj2, new_bestand.first())

        # obj3 has one dubletten bestand; this should add a bestand
        all_bestand = list(self.obj3.bestand_set.values_list('lagerort', flat=True))
        expected = [self.dubletten_lagerort.pk, self.bestand_lagerort.pk]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj3.bestand_set.exclude(pk__in=old_bestand3)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj3, new_bestand.first())

        # obj4 has both bestand and dubletten bestand; this should add a dublette
        all_bestand = list(self.obj4.bestand_set.values_list('lagerort', flat=True))
        expected = [
            self.bestand_lagerort.pk, self.dubletten_lagerort.pk,
            self.dubletten_lagerort.pk
        ]
        self.assertEqual(all_bestand, expected)
        new_bestand = self.obj4.bestand_set.exclude(pk__in=old_bestand4)
        self.assertEqual(new_bestand.count(), 1)
        self.assertLoggedAddition(self.obj4, new_bestand.first())

    def test_get_initial(self):
        view = self.get_view()
        initial = view.get_initial()

        self.assertTrue('bestand' in initial)
        self.assertEqual(initial.get('bestand'), self.bestand_lagerort)
        self.assertTrue('dublette' in initial)
        self.assertEqual(initial.get('dublette'), self.dubletten_lagerort)

    def test_permissions_required(self):
        # Assert that specific permissions are required to access this action.
        view = self.get_view()
        self.assertTrue(hasattr(view, 'allowed_permissions'))
        self.assertEqual(view.allowed_permissions, ['alter_bestand'])


class TestMergeViewWizardedAusgabe(ActionViewTestCase):
    # Note that tests concerning logging for this view are done on
    # test_utils.merge_records directly.

    view_class = MergeViewWizarded
    model = _models.Ausgabe
    model_admin_class = AusgabenAdmin
    raw_data = [
        {'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000]},
        {'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001], 'jahrgang':1},
        {'magazin__magazin_name': 'Bad', 'ausgabejahr__jahr': [2001], 'jahrgang': 20},
        {'magazin__magazin_name': 'Testmagazin', 'jahrgang': 2}
    ]

    def test_action_allowed(self):
        queryset = self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view = self.get_view(queryset=queryset)
        self.assertTrue(view.action_allowed)

    def test_action_allowed_low_qs_count(self):
        request = self.post_request()
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
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
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
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        form_data = {'0-primary': self.obj1.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)

        # Step 1
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
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        form_data = {'0-primary': self.obj1.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.changelist_path)

    def test_merge_not_updating_fields_it_should_not(self):
        # Check that the whole process does *NOT* change already present data
        # of the selected primary object.
        # spice up obj1 so we can verify that a merge has happened:
        self.qs_obj1.update(beschreibung='I really should not be here.')
        request_data = {
            'action': 'merge_records',
            helpers.ACTION_CHECKBOX_NAME: [self.obj1.pk, self.obj2.pk, self.obj4.pk]
        }
        management_form = {'merge_view_wizarded-current_step': 0}
        request_data.update(management_form)
        # Select obj2 (or obj4) here as primary as it already has a value for
        # jahrgang (our only 'source' of conflict):
        form_data = {'0-primary': self.obj2.pk, '0-expand_primary': True}
        request_data.update(form_data)

        response = self.client.post(self.changelist_path, data=request_data)

        self.assertEqual(response.status_code, 302, msg="Redirect expected.")
        self.assertEqual(
            response.url, self.changelist_path,
            msg="Redirect back to changelist expected."
        )

        self.obj2.refresh_from_db()
        self.assertEqual(self.obj2.jahrgang, 1)
        self.assertEqual(self.obj2.beschreibung, 'I really should not be here.')

    @patch('DBentry.actions.views.get_updateable_fields', return_value=[])
    @patch.object(SessionWizardView, 'process_step', return_value={})
    def test_process_step(self, super_process_step, updateable_fields):
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
        super_process_step.return_value = {'0-primary': self.obj1.pk}
        form.cleaned_data = {'0-primary': self.obj1.pk, 'expand_primary': True}
        self.assertEqual(view.process_step(form), {'0-primary': self.obj1.pk})

        # obj1 can be updated on the field 'jahrgang' with obj2's value
        updateable_fields.return_value = ['jahrgang']
        view.queryset = self.model.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk])
        view.storage.current_step = ''
        processed_data = view.process_step(form)
        self.assertIn('updates', processed_data)
        self.assertIn('jahrgang', processed_data['updates'])
        self.assertEqual(processed_data['updates']['jahrgang'], ['1'])
        self.assertEqual(view.storage.current_step, last_step)

        # same as above, but with a conflict due to involving obj4 as well
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
    def test_get_context_data(self, super_get_context_data):
        # Assert that 'title' is counting up with 'step'
        view = self.get_view()
        view.steps = Mock(current='0')
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 1')
        view.steps.current = '22'
        self.assertEqual(view.get_context_data().get('title'), 'Merge objects: step 23')

    @patch.object(WizardView, 'get_form_kwargs', return_value={})
    def test_get_form_kwargs_select_primary(self, super_get_form_kwargs):
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
    def test_get_form_kwargs_conflicts(self, super_get_form_kwargs):
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

    @patch('DBentry.actions.views.merge_records')
    @patch.object(MergeViewWizarded, 'get_cleaned_data_for_step')
    def test_perform_action_no_expand(self, mocked_step_data, mocked_merge_records):
        # Assert that merge_records is called with the correct arguments.
        # Also check that no 'updates' are passed to merge_records if
        # expand_primary is False.
        step_data = {'primary': self.obj1.pk, 'expand_primary': False}
        mocked_step_data.return_value = step_data

        view = self.get_view(queryset=self.queryset)
        # Set the property's private attribute:
        view._updates = {'some_update': 'that_should not be used'}
        view.perform_action()
        self.assertTrue(mocked_merge_records.called)
        args, kwargs = mocked_merge_records.call_args
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
        self.form_cleaned_data = [
            {
                'titel': 'Testausgabe', 'ausgabe_id': self.obj1.pk, 'accept': True,
            }
        ]
        self.mag = self.obj1.magazin

    @translation_override(language=None)
    def test_action_allowed_has_artikels(self):
        self.obj1.artikel_set.add(make(_models.Artikel, ausgabe=self.obj1))
        request = self.post_request()
        view = self.get_view(request=request, queryset=self.queryset)
        self.assertFalse(view.action_allowed)
        expected_message = (
            "Aktion abgebrochen: Folgende Ausgaben besitzen Artikel, die nicht "
            "verschoben werden können: {}"
        ).format(
            '<a href="/admin/DBentry/ausgabe/{}/change/">Testausgabe</a>'.format(
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
        self.assertEqual(initial[0]['ausgabe_id'], self.obj1.pk)
        self.assertIn('titel', initial[0])
        self.assertEqual(initial[0]['titel'], self.obj1.magazin.magazin_name)
        self.assertIn('zusammenfassung', initial[0])
        self.assertEqual(initial[0]['zusammenfassung'], self.obj1.magazin.beschreibung)
        self.assertIn('beschreibung', initial[0])
        self.assertEqual(initial[0]['beschreibung'], self.obj1.beschreibung)
        self.assertIn('bemerkungen', initial[0])
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

    @patch('DBentry.actions.views.get_model_from_string')
    def test_perform_action_protected_ausgabe(self, mocked_model_from_string):
        mocked_model_from_string.return_value = _models.Brochure
        options_form_cleaned_data = {'brochure_art': 'brochure'}

        self.obj1.artikel_set.add(make(_models.Artikel, ausgabe_id=self.obj1.pk))
        request = self.get_request()
        view = self.get_view(request=request, queryset=self.queryset)
        view.mag = self.mag

        view.perform_action(self.form_cleaned_data, options_form_cleaned_data)
        self.assertTrue(self.model.objects.filter(pk=self.obj1.pk).exists())
        expected_message = (
            'Folgende Ausgaben konnten nicht gelöscht werden: '
            '<a href="/admin/DBentry/ausgabe/{pk}/change/" target="_blank">{name}</a> '
            '(<a href="/admin/DBentry/ausgabe/?id__in={pk}" target="_blank">Liste</a>). '
            'Es wurden keine Broschüren für diese Ausgaben erstellt.'
        ).format(pk=self.obj1.pk, name=str(self.obj1))
        self.assertMessageSent(request, expected_message)

        # No new brochure objects should have been created
        self.assertEqual(_models.Brochure.objects.count(), 0)

    @patch('DBentry.actions.views.is_protected')
    @patch('DBentry.actions.views.get_model_from_string')
    def test_perform_action_does_not_roll_back_ausgabe_deletion(
            self, mocked_model_from_string, mocked_is_protected):
        # Assert that a rollback on trying to delete the magazin does not also
        # roll back the ausgabe.
        mocked_model_from_string.return_value = _models.Brochure
        mocked_is_protected.return_value = False
        options_form_cleaned_data = {'brochure_art': 'brochure', 'delete_magazin': True}

        ausgabe_id = self.obj1.pk
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
        'DBentry.actions.views.MoveToBrochureBase.can_delete_magazin',
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
        view._magazin_instance = self.obj1.magazin
        self.assertTrue(view.can_delete_magazin)

        # Add another ausgabe to magazin to forbid the deletion of it.
        make(self.model, magazin=self.obj1.magazin)
        view = self.get_view(
            self.get_request(), queryset=self.model.objects.filter(pk=self.obj1.pk))
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
        changelist_post_data[helpers.ACTION_CHECKBOX_NAME] = [self.obj1.pk, obj2.pk]
        response = self.client.post(path=self.changelist_path, data=changelist_post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.view_class.template_name, [t.name for t in response.templates],
            msg="Should be rendering the MoveToBrochure template."
        )

        # User selects the 'Katalog' category and confirms, without having
        # checked the delete_magazin checkbox.
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
