from typing import Union
from unittest.mock import Mock, patch

from django.contrib import admin, contenttypes
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.main import ALL_VAR, ORDER_VAR
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.db import connections, transaction
from django.db.models import Count, Exists, Func, Min, Subquery
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.translation import override as translation_override

import dbentry.admin as _admin
import dbentry.models as _models
from dbentry.changelist import AusgabeChangeList, BestandChangeList
from dbentry.sites import miz_site
from tests.case import AdminTestCase
from tests.model_factory import make


class AdminTestMethodsMixin(object):
    admin_site = miz_site

    # Fields to be excluded from the changeview form:
    exclude_expected = ()
    # Fields expected to be on the changeview form:
    fields_expected = ()
    # The number of queries expected for a changelist request:
    # Commonly, it is 5 queries: 1. session, 2. auth, 3. result count,
    # 4. full count, 5. result list
    num_queries_changelist = 5

    def get_annotated_model_obj(self: Union['AdminTestMethodsMixin', 'AdminTestCase'], obj):
        """Apply the model_admin's changelist annotations to the given object."""
        return (
            self.queryset
            .filter(pk=obj.pk)
            .annotate(**self.model.get_overview_annotations())
            .get()
        )

    def test_get_exclude(self: Union['AdminTestMethodsMixin', 'AdminTestCase']):
        """Assert that the expected fields are excluded from change form."""
        self.assertCountEqual(
            self.model_admin.get_exclude(self.get_request()),
            self.exclude_expected
        )

    def test_get_fields(self: Union['AdminTestMethodsMixin', 'AdminTestCase']):
        """Assert that the expected fields are used for the change form."""
        self.assertSequenceEqual(
            self.model_admin.get_fields(self.get_request()),
            self.fields_expected
        )

    def test_changelist_can_be_reached(self: Union['AdminTestMethodsMixin', 'AdminTestCase']):
        """Assert that the changelist can be reached."""
        response = self.client.get(path=self.changelist_path)
        self.assertEqual(response.status_code, 200)

    def test_add_page_can_be_reached(self: Union['AdminTestMethodsMixin', 'AdminTestCase']):
        """Assert that the add page can be reached."""
        response = self.client.get(path=self.add_path)
        self.assertEqual(response.status_code, 200)

    def test_changelist_queries(self: Union['AdminTestMethodsMixin', 'AdminTestCase']):
        """
        Assert that the number of queries needed for the changelist remains
        constant and doesn't depend on the number of records fetched.
        """
        # Request with 'all=1' to set changelist.show_all to True which should
        # stop hiding/filtering results - which might affect the # of queries.
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path, data={ALL_VAR: '1'})
        n = len(queries.captured_queries)
        make(self.model)
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path, data={ALL_VAR: '1'})
        self.assertEqual(
            n, len(queries.captured_queries),
            msg="Number of queries for changelist depends on number of records! "
                f"Unoptimized query / no prefetching?"
        )
        if self.num_queries_changelist:
            self.assertEqual(
                n, self.num_queries_changelist,
                msg="Number of queries required for a changelist request differs "
                    f"from the expected value: got '{n}' expected '{self.num_queries_changelist}'. "
                    "Check 'list_select_related'."
            )


class TestArtikelAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.ArtikelAdmin
    model = _models.Artikel
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort',
        'spielort', 'veranstaltung'
    ]
    fields_expected = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'),
        'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj1 = make(
            _models.Artikel, ausgabe__magazin=cls.mag, seite=1, schlagzeile='Test!',  # noqa
            schlagwort__schlagwort=['Schlagwort1', 'Schlagwort2'],
            musiker__kuenstler_name='Alice Tester', band__band_name='Testband'
        )
        super().setUpTestData()

    def test_ausgabe_name(self):
        self.assertEqual(self.model_admin.ausgabe_name(self.obj1), self.obj1.ausgabe._name)

    def test_zusammenfassung_string(self):
        self.assertEqual(self.model_admin.zusammenfassung_string(self.obj1), '-')
        self.obj1.zusammenfassung = (
            "Dies ist eine Testzusammenfassung, die nicht besonders inhaltsvoll "
            "ist, dafür aber doch recht lang ist."
        )
        self.assertEqual(
            self.model_admin.zusammenfassung_string(self.obj1),
            "Dies ist eine Testzusammenfassung, die nicht besonders inhaltsvoll "
            "ist, dafür aber doch recht lang [...]"
        )

    def test_artikel_magazin(self):
        self.assertEqual(self.model_admin.artikel_magazin(self.obj1), self.mag.magazin_name)

    def test_schlagwort_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.schlagwort_string(obj), 'Schlagwort1, Schlagwort2')

    def test_kuenstler_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.kuenstler_list(obj), 'Testband, Alice Tester')


class TestAudioAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.AudioAdmin
    model = _models.Audio
    exclude_expected = [
        'plattenfirma', 'band', 'genre', 'musiker', 'person', 'schlagwort',
        'spielort', 'veranstaltung', 'ort'
    ]
    fields_expected = [
        'titel', 'tracks', 'laufzeit', 'jahr', 'land_pressung', 'quelle', 'original',
        'plattennummer', 'release_id', 'discogs_url', 'beschreibung',
        'bemerkungen', 'medium', 'medium_qty'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, band__band_name='Testband', musiker__kuenstler_name='Alice Tester'
        )
        super().setUpTestData()

    def test_kuenstler_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.kuenstler_list(obj), 'Testband, Alice Tester')

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestAusgabenAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.AusgabenAdmin
    model = _models.Ausgabe
    exclude_expected = ['audio', 'video']
    fields_expected = [
        'magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang',
        'beschreibung', 'bemerkungen'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            _models.Ausgabe,
            magazin__magazin_name='Testmagazin',
            ausgabejahr__jahr=[2020, 2021, 2022],
            ausgabenum__num=[10, 11, 12],
            ausgabelnum__lnum=[10, 11, 12],
            ausgabemonat__monat__monat=['Januar', 'Februar'],
            artikel__schlagzeile='Test', artikel__seite=1,
            bestand__lagerort__ort=['Zeitschriftenraum', 'Dublettenlager'],
        )
        super().setUpTestData()

    def test_changelist_queries(self):
        """
        Assert that the number of queries needed for the changelist remains
        constant and doesn't depend on the number of records fetched.
        """
        # Request with 'all=1' to set changelist.show_all to True which should
        # stop hiding/filtering results - which might affect the # of queries.
        # Add ORDER_VAR parameter to suppress chronological ordering.
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path, data={ALL_VAR: '1', ORDER_VAR: '1'})
        n = len(queries.captured_queries)
        make(self.model)
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path, data={ALL_VAR: '1', ORDER_VAR: '1'})
        self.assertEqual(
            n, len(queries.captured_queries),
            msg="Number of queries for changelist depends on number of records! "
                f"Unoptimized query / no prefetching?"
        )
        if self.num_queries_changelist:
            self.assertEqual(
                n, self.num_queries_changelist,
                msg="Number of queries required for a changelist request differs "
                    f"from the expected value: got '{n}' expected '{self.num_queries_changelist}'. "
                    "Check 'list_select_related'."
            )

    def test_get_changelist(self):
        """Assert that AusgabenAdmin uses the AusgabeChangeList changelist class."""
        self.assertEqual(self.model_admin.get_changelist(self.get_request()), AusgabeChangeList)

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('jahr_list', annotations)
        self.assertIsInstance(annotations['jahr_list'], Func)
        self.assertIn('num_list', annotations)
        self.assertIsInstance(annotations['num_list'], Func)
        self.assertIn('lnum_list', annotations)
        self.assertIsInstance(annotations['lnum_list'], Func)
        self.assertIn('monat_list', annotations)
        self.assertIsInstance(annotations['monat_list'], Subquery)
        self.assertIn('anz_artikel', annotations)
        self.assertIsInstance(annotations['anz_artikel'], Count)

    def test_ausgabe_name(self):
        self.assertEqual(self.model_admin.ausgabe_name(self.obj1), self.obj1._name)

    def test_magazin_name(self):
        self.assertEqual(self.model_admin.magazin_name(self.obj1), self.obj1.magazin.magazin_name)

    def test_anz_artikel(self):
        self.assertEqual(self.model_admin.anz_artikel(self.get_annotated_model_obj(self.obj1)), 1)

        _models.Artikel.objects.all().delete()
        self.assertEqual(self.model_admin.anz_artikel(self.get_annotated_model_obj(self.obj1)), 0)

    def test_jahr_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.jahr_list(obj), '2020, 2021, 2022')

    def test_num_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.num_list(obj), '10, 11, 12')

    def test_lnum_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.lnum_list(obj), '10, 11, 12')

    def test_monat_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.monat_list(obj), 'Jan, Feb')

    def test_change_status_unbearbeitet(self):
        self.model_admin.change_status_unbearbeitet(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'unb'})

    def test_change_status_inbearbeitung(self):
        self.model_admin.change_status_inbearbeitung(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'iB'})

    def test_change_status_abgeschlossen(self):
        self.model_admin.change_status_abgeschlossen(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'abg'})

    def test_change_status_action(self):
        """
        Assert that the status of an Ausgabe object can be changed via the
        appropriate action.
        """
        test_data = [
            ('change_status_inbearbeitung', 'iB'),
            ('change_status_abgeschlossen', 'abg'),
            # obj1.status is 'unb' at the start, so test for 'unb' last to be
            # able to register a change:
            ('change_status_unbearbeitet', 'unb')
        ]
        for action, expected_value in test_data:
            request_data = {
                'action': action,
                admin.helpers.ACTION_CHECKBOX_NAME: self.obj1.pk,
                'index': 0,  # required by changelist_view to identify the request as an action
            }
            path = self.changelist_path + f'?magazin={self.obj1.magazin.id}'
            with self.subTest(action=action, status=expected_value):
                with transaction.atomic():
                    response = self.client.post(path, data=request_data)
                self.assertEqual(response.status_code, 302)
                self.obj1.refresh_from_db()
                self.assertEqual(self.obj1.status, expected_value)

    @patch('dbentry.admin.log_change')
    def test_change_status_logentry_error(self, log_change_mock):
        """
        Assert that exceptions raised during the creation of LogEntry objects
        are caught.
        """
        log_change_mock.side_effect = ValueError("This is a test exception.")

        with patch.object(self.model_admin, 'message_user') as message_user_mock:
            # No exception should propagate beyond _change_status:
            with self.assertNotRaises(Exception):
                self.model_admin._change_status(
                    self.get_request(), self.queryset, status=_models.Ausgabe.Status.INBEARBEITUNG
                )
                log_change_mock.assert_called()

        # An exception should not stop the updates to model instances:
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'iB'})
        # The user should have been messaged about the exception:
        _request, message, level = message_user_mock.call_args[0]
        self.assertEqual(level, 'ERROR')
        self.assertEqual(
            message,
            "Fehler beim Erstellen der LogEntry Objekte: \nValueError: This is a test exception."
        )

    def test_movetobrochure_permissions(self):
        """Assert that the moveto_brochure action requires certain permissions."""
        msg_template = (
            "Action 'moveto_brochure' should not be available to "
            "users that miss the '%s' permission."
        )
        delete_codename = get_permission_codename('delete', _models.Ausgabe._meta)
        delete_permission = Permission.objects.get(
            codename=delete_codename,
            content_type=ContentType.objects.get_for_model(_models.Ausgabe)
        )
        add_codename = get_permission_codename('add', _models.BaseBrochure._meta)
        add_permission = Permission.objects.get(
            codename=add_codename,
            content_type=ContentType.objects.get_for_model(_models.BaseBrochure)
        )

        user = User.objects.create(username='Alice', password='bob_sucks', is_staff=True)
        # Note that each request will need a *new* user instance, since the
        # auth backend does some permission caching on the passed in instances.

        # delete only: not allowed
        user.user_permissions.set([delete_permission])
        request = self.get_request(user=User.objects.get(pk=user.id))
        self.assertFalse(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=msg_template % add_codename
        )

        # add only: not allowed
        user.user_permissions.set([add_permission])
        request = self.get_request(user=User.objects.get(pk=user.id))
        self.assertFalse(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=msg_template % delete_codename
        )

        # delete + add: moveto_brochure allowed
        user.user_permissions.set([delete_permission, add_permission])
        request = self.get_request(user=User.objects.get(pk=user.id))
        self.assertTrue(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=(
                    "Action 'moveto_brochure' should be available for users with both "
                    "'%s' and '%s' permissions" % (delete_codename, add_codename)
            )
        )

    def test_actions_no_permissions(self):
        """Assert that certain actions are not available to user without permissions."""
        actions = self.model_admin.get_actions(self.get_request(user=self.noperms_user))
        action_names = (
            'bulk_jg', 'change_bestand', 'moveto_brochure', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertNotIn(action_name, actions)

    def test_actions_staff_user(self):
        """
        Assert that certain actions are available to staff users with the
        proper permissions.
        """
        # bulk_jg requires 'change' and moveto_brochure requires 'delete':
        ct = ContentType.objects.get_for_model(self.model)
        for perm_name in ('change', 'delete', 'merge'):
            codename = get_permission_codename(perm_name, self.model._meta)
            self.staff_user.user_permissions.add(
                Permission.objects.get(codename=codename, content_type=ct)
            )
        # Add permissions for 'change_bestand':
        ct = ContentType.objects.get_for_model(_models.Bestand)
        for action in ('add', 'change', 'delete'):
            codename = get_permission_codename(action, _models.Bestand._meta)
            self.staff_user.user_permissions.add(
                Permission.objects.get(codename=codename, content_type=ct)
            )

        actions = self.model_admin.get_actions(self.get_request(user=self.staff_user))
        action_names = (
            'bulk_jg', 'change_bestand', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertIn(action_name, actions)

    def test_actions_super_user(self):
        """Assert that all actions are available to superusers."""
        actions = self.model_admin.get_actions(self.get_request(user=self.super_user))
        action_names = (
            'bulk_jg', 'change_bestand', 'moveto_brochure', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertIn(action_name, actions)

    def test_brochure_changelist_link(self):
        """Assert that the links to each of the BaseBrochure models are labelled correctly."""
        obj = make(self.model)
        make(_models.Brochure, ausgabe=obj)
        make(_models.Kalender, ausgabe=obj)
        make(_models.Katalog, ausgabe=obj)
        changelist_links = self.model_admin.add_changelist_links(object_id=obj.pk, labels={})
        labels = {
            'brochure': 'Broschüren (1)',
            'kalender': 'Programmhefte (1)',
            'katalog': 'Warenkataloge (1)'
        }
        for model in (_models.Brochure, _models.Kalender, _models.Katalog):
            opts = model._meta
            with self.subTest(model=opts.model_name):
                url_name = f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist"
                expected = {
                    'url': f"{reverse(url_name)}?{obj._meta.model_name}={obj.pk}",
                    'label': labels[opts.model_name]
                }
                self.assertIn(expected, changelist_links)

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestAutorAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.AutorAdmin
    model = _models.Autor
    exclude_expected = ['magazin']
    fields_expected = ['kuerzel', 'beschreibung', 'bemerkungen', 'person']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, magazin__magazin_name=['Testmagazin1', 'Testmagazin2'])
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('magazin_list', annotations)
        self.assertIsInstance(annotations['magazin_list'], Func)

    def test_autor_name(self):
        self.assertEqual(self.model_admin.autor_name(self.obj1), self.obj1._name)

    def test_magazin_string(self):
        obj = self.get_annotated_model_obj(self.obj1)  # noqa
        self.assertEqual(self.model_admin.magazin_string(obj), 'Testmagazin1, Testmagazin2')


class TestBandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BandAdmin
    model = _models.Band
    exclude_expected = ['genre', 'musiker', 'orte']
    fields_expected = ['band_name', 'beschreibung', 'bemerkungen']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, bandalias__alias=['Alias1', 'Alias2'],
            genre__genre=['Testgenre1', 'Testgenre2'],
            musiker__kuenstler_name=['Kuenstler 1', 'Kuenstler 2']
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('genre_list', annotations)
        self.assertIsInstance(annotations['genre_list'], Func)
        self.assertIn('musiker_list', annotations)
        self.assertIsInstance(annotations['musiker_list'], Func)
        self.assertIn('alias_list', annotations)
        self.assertIsInstance(annotations['alias_list'], Func)
        self.assertIn('orte_list', annotations)
        self.assertIsInstance(annotations['orte_list'], Func)

    def test_genre_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.genre_string(obj), 'Testgenre1, Testgenre2')

    def test_musiker_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.musiker_string(obj), 'Kuenstler 1, Kuenstler 2')

    def test_alias_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.alias_string(obj), 'Alias1, Alias2')

    def test_orte_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.orte_string(obj), '-')

        self.obj1.orte.add(make(_models.Ort, stadt='Dortmund', land__code='XYZ'))
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.orte_string(obj), 'Dortmund, XYZ')


class TestBestandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BestandAdmin
    model = _models.Bestand
    fields_expected = [
        'lagerort', 'anmerkungen', 'provenienz', 'audio', 'ausgabe', 'brochure', 'buch',
        'dokument', 'foto', 'memorabilien', 'plakat', 'technik', 'video'
    ]
    num_queries_changelist = 0  # skip the test for the number of queries per changelist request

    @classmethod
    def setUpTestData(cls):
        cls.audio_object = make(_models.Audio, titel="Hovercrafts Full of Eels")
        cls.bestand_object = make(_models.Bestand, audio=cls.audio_object)  # noqa
        super().setUpTestData()

    def test_get_changelist(self):
        """Assert that BestandAdmin uses the BestandChangeList changelist class."""
        self.assertEqual(self.model_admin.get_changelist(None), BestandChangeList)

    def test_cache_bestand_data(self):
        """
        Assert that cache_bestand_data builds a cache containing 'bestand_class'
        and 'bestand_link' for each object in the changelist result list.
        """
        self.model_admin.cache_bestand_data(
            self.get_request(), result_list=self.queryset,
            bestand_fields=[self.model._meta.get_field('audio')]
        )

        self.assertTrue(getattr(self.model_admin, '_cache', None))
        cache = self.model_admin._cache
        self.assertIn(self.bestand_object.pk, cache)
        self.assertIn('bestand_class', cache[self.bestand_object.pk])
        self.assertEqual('Audio Material', cache[self.bestand_object.pk]['bestand_class'])
        self.assertIn('bestand_link', cache[self.bestand_object.pk])
        self.assertTrue(cache[self.bestand_object.pk]['bestand_link'].startswith('<a'))

    def test_changelist_cache(self):
        """Assert that requesting a changelist creates the bestand data cache."""
        self.assertFalse(getattr(self.model_admin, '_cache', None))
        self.model_admin.get_changelist_instance(self.get_request(path=self.changelist_path))
        self.assertTrue(getattr(self.model_admin, '_cache', None))

    def test_bestand_class(self):
        """
        Assert that list_display method bestand_class returns the verbose_name
        of the model that is referenced by the particular Bestand instance.
        """
        unrelated_object = make(self.model)
        self.model_admin.cache_bestand_data(
            self.get_request(), self.queryset,
            bestand_fields=[self.model._meta.get_field('audio')]
        )

        self.assertEqual('Audio Material', self.model_admin.bestand_class(self.bestand_object))
        # This object has no relations; the 'bestand_class' should be an empty
        # string.
        self.assertFalse(self.model_admin.bestand_class(unrelated_object))
        # The cache won't have an entry for this new object; expect an empty
        # string.
        new_object = make(self.model)
        self.assertFalse(self.model_admin.bestand_class(new_object))

    def test_bestand_link(self):
        """
        Assert that list_display method bestand_link returns a hyperlink to
        the instance that is referenced by the particular Bestand instance.
        """
        unrelated_object = make(self.model)
        self.model_admin.cache_bestand_data(
            self.get_request(), self.queryset,
            bestand_fields=[self.model._meta.get_field('audio')]
        )

        link = self.model_admin.bestand_link(self.bestand_object)
        self.assertTrue(link.startswith('<a'))
        self.assertIn('target="_blank"', link)
        self.assertIn(str(self.bestand_object.audio.pk), link)
        # This object has no relations; the link should be an empty string.
        self.assertFalse(self.model_admin.bestand_class(unrelated_object))
        # The cache won't have an entry for this new object; expect an empty
        # string.
        new_object = make(self.model)
        self.assertFalse(self.model_admin.bestand_class(new_object))


class TestBlandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BlandAdmin
    model = _models.Bundesland
    fields_expected = ['bland_name', 'code', 'land']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestBaseBrochureAdmin(AdminTestCase):
    admin_site = miz_site
    model_admin_class = _admin.BaseBrochureAdmin
    model = _models.Brochure

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, jahre__jahr=[2002, 2001])
        super().setUpTestData()

    @translation_override(language=None)
    def test_get_fieldsets(self):
        """Assert that an extra fieldset for the (ausgabe__magazin, ausgabe) group is added."""
        fieldsets = self.model_admin.get_fieldsets(self.get_request())
        # Expect three fieldsets:
        #   1) the default 'none',
        #   2) beschreibung & bemerkungen
        #   3) ausgabe & ausgabe__magazin
        self.assertEqual(len(fieldsets), 3)

        self.assertEqual(fieldsets[1][0], 'Beilage von Ausgabe')
        fieldset_options = fieldsets[1][1]
        self.assertIn('fields', fieldset_options)
        self.assertEqual(fieldset_options['fields'], [('ausgabe__magazin', 'ausgabe')])
        self.assertIn('description', fieldset_options)
        self.assertEqual(
            fieldset_options['description'],
            'Geben Sie die Ausgabe an, der dieses Objekt beilag.'
        )

    def test_get_queryset_adds_jahr_min_annotation(self):
        """Assert that the 'jahr_min' annotation is added to the queryset."""
        queryset = self.model_admin.get_queryset(self.get_request())
        annotations = queryset.query.annotations
        self.assertIn('jahr_min', annotations)
        self.assertEqual(annotations['jahr_min'], Min('jahre__jahr'))

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('jahr_list', annotations)
        self.assertIsInstance(annotations['jahr_list'], Func)

    def test_jahr_list(self):
        obj = (
            self.queryset
            .filter(pk=self.obj1.pk)
            .annotate(**self.model.get_overview_annotations())
            .get()
        )
        self.assertEqual(self.model_admin.jahr_list(obj), '2001, 2002')


class TestBrochureAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BrochureAdmin
    model = _models.Brochure
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'ausgabe__magazin'
    ]
    exclude_expected = ['genre', 'schlagwort']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestBuchAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BuchAdmin
    model = _models.Buch
    exclude_expected = [
        'herausgeber', 'verlag', 'autor', 'genre', 'schlagwort', 'person', 'band',
        'musiker', 'ort', 'spielort', 'veranstaltung'
    ]
    fields_expected = [
        'titel', 'titel_orig', 'seitenumfang', 'jahr', 'jahr_orig', 'auflage',
        'EAN', 'ISBN', 'is_buchband', 'beschreibung', 'bemerkungen',
        'schriftenreihe', 'buchband', 'sprache',
    ]

    @classmethod
    def setUpTestData(cls):
        p1 = make(_models.Person, vorname='Alice', nachname='Testman')
        p2 = make(_models.Person, vorname='Bob', nachname='Mantest')
        cls.musiker = make(_models.Musiker, kuenstler_name='Robert Plant')
        cls.band = make(_models.Band, band_name='Led Zeppelin')
        cls.obj1 = make(
            cls.model,
            autor__person=[p1, p2],
            schlagwort__schlagwort=['Schlagwort1', 'Schlagwort2'],
            genre__genre=['Testgenre1', 'Testgenre2'],
            musiker=[cls.musiker],  # noqa
            band=[cls.band]  # noqa
        )
        cls.test_data = [cls.obj1]  # noqa
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('autor_list', annotations)
        self.assertIsInstance(annotations['autor_list'], Func)
        self.assertIn('schlagwort_list', annotations)
        self.assertIsInstance(annotations['schlagwort_list'], Func)
        self.assertIn('genre_list', annotations)
        self.assertIsInstance(annotations['genre_list'], Func)
        self.assertIn('kuenstler_list', annotations)
        self.assertIsInstance(annotations['kuenstler_list'], Func)

    def test_autoren_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(
            self.model_admin.autoren_string(obj),
            'Alice Testman (AT), Bob Mantest (BM)'
        )

    def test_schlagwort_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.schlagwort_string(obj), 'Schlagwort1, Schlagwort2')

    def test_genre_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.genre_string(obj), 'Testgenre1, Testgenre2')

    def test_kuenstler_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.kuenstler_list(obj), 'Led Zeppelin, Robert Plant')

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestDateiAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DateiAdmin
    model = _models.Datei
    fields_expected = [
        'titel', 'media_typ', 'datei_pfad', 'beschreibung', 'bemerkungen', 'provenienz']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestDokumentAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DokumentAdmin
    model = _models.Dokument
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestFotoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.FotoAdmin
    model = _models.Foto
    fields_expected = [
        'titel', 'foto_id', 'size', 'typ', 'farbe', 'datum', 'reihe',
        'owner', 'beschreibung', 'bemerkungen'
    ]
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band',
        'musiker', 'ort', 'spielort', 'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, datum='2022-10-17', schlagwort__schlagwort=['Foo', 'Bar'])
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('schlagwort_list', annotations)
        self.assertIsInstance(annotations['schlagwort_list'], Func)

    def test_foto_id(self):
        """Assert that foto_id returns the id padded with zeroes."""
        self.assertEqual(self.model_admin.foto_id(self.obj1), f"{self.obj1.pk:06}")

    def test_datum_localized(self):
        self.obj1.refresh_from_db()
        with translation_override(language=None):
            self.assertEqual(self.model_admin.datum_localized(self.obj1), '17. October 2022')

    def test_schlagwort_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.schlagwort_list(obj), 'Bar, Foo')


class TestGenreAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.GenreAdmin
    model = _models.Genre
    fields_expected = ['genre']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, genre='Sub Genre', genrealias__alias=['Alias1', 'Alias2'])
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('alias_list', annotations)
        self.assertIsInstance(annotations['alias_list'], Func)

    def test_alias_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.alias_string(obj), 'Alias1, Alias2')

    def test_brochure_changelist_link(self):
        """Assert that the links to each of the BaseBrochure models are labelled correctly."""
        obj = make(self.model)
        make(_models.Brochure, genre=obj)
        make(_models.Kalender, genre=obj)
        make(_models.Katalog, genre=obj)
        changelist_links = self.model_admin.add_changelist_links(object_id=obj.pk, labels={})
        labels = {
            'brochure': 'Broschüren (1)',
            'kalender': 'Programmhefte (1)',
            'katalog': 'Warenkataloge (1)'
        }
        for model in (_models.Brochure, _models.Kalender, _models.Katalog):
            opts = model._meta
            with self.subTest(model=opts.model_name):
                url_name = f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist"
                expected = {
                    'url': f"{reverse(url_name)}?{obj._meta.model_name}={obj.pk}",
                    'label': labels[opts.model_name]
                }
                self.assertIn(expected, changelist_links)


class TestHerausgeberAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.HerausgeberAdmin
    model = _models.Herausgeber
    fields_expected = ['herausgeber']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestInstrumentAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.InstrumentAdmin
    model = _models.Instrument
    fields_expected = ['instrument', 'kuerzel']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestKalenderAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KalenderAdmin
    model = _models.Kalender
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'ausgabe__magazin'
    ]
    exclude_expected = ['genre', 'spielort', 'veranstaltung']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestKatalogAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KatalogAdmin
    model = _models.Katalog
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'art', 'ausgabe__magazin'
    ]
    exclude_expected = ['genre']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_get_fieldsets(self):
        """Assert that the fields 'art' and 'zusammenfassung' are swapped."""
        none_fieldset_options = self.model_admin.get_fieldsets(self.get_request())[0][1]
        self.assertIn('fields', none_fieldset_options)
        self.assertIn('art', none_fieldset_options['fields'])
        art_index = none_fieldset_options['fields'].index('art')
        self.assertIn('zusammenfassung', none_fieldset_options['fields'])
        z_index = none_fieldset_options['fields'].index('zusammenfassung')
        self.assertTrue(art_index < z_index)

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestLandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.LandAdmin
    model = _models.Land
    fields_expected = ['land_name', 'code']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestMagazinAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.MagazinAdmin
    model = _models.Magazin
    exclude_expected = ['genre', 'verlag', 'herausgeber', 'orte']
    fields_expected = [
        'magazin_name', 'ausgaben_merkmal', 'fanzine', 'issn',
        'beschreibung', 'bemerkungen',
    ]

    @classmethod
    def setUpTestData(cls):
        ort1 = make(_models.Ort, stadt='Dortmund', land__code='DE')
        ort2 = make(_models.Ort, stadt='Buxtehude', land__code='DE')
        cls.beschreibung = (
            "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor"
            " invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et"
            " accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata "
            "sanctus est Lorem ipsum dolor sit amet."
        )
        cls.obj1 = make(
            cls.model, ausgabe__extra=1, orte=[ort1, ort2], beschreibung=cls.beschreibung  # noqa
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('orte_list', annotations)
        self.assertIsInstance(annotations['orte_list'], Func)
        self.assertIn('anz_ausgaben', annotations)
        self.assertIsInstance(annotations['anz_ausgaben'], Count)

    def test_anz_ausgaben(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.anz_ausgaben(obj), 1)
        self.obj1.ausgabe_set.all().delete()
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.anz_ausgaben(obj), 0)

    def test_orte_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.orte_string(obj), 'Buxtehude, DE; Dortmund, DE')

    def test_short_beschreibung(self):
        self.assertGreater(
            len(self.beschreibung),
            len(self.model_admin.short_beschreibung(self.obj1))
        )

    def test_ausgaben_merkmal_excluded(self):
        """Assert that field 'ausgaben_merkmal' is only included for superusers."""
        ct = ContentType.objects.get_for_model(self.model)
        codename = get_permission_codename('change', self.model._meta)
        self.staff_user.user_permissions.add(
            Permission.objects.get(codename=codename, content_type=ct)
        )

        self.assertIn(
            'ausgaben_merkmal',
            self.model_admin.get_exclude(self.get_request(user=self.staff_user)),
            msg="Non-superuser users should not have access to field 'ausgaben_merkmal'."
        )
        self.assertNotIn(
            'ausgaben_merkmal',
            self.model_admin.get_exclude(self.get_request(user=self.super_user)),
            msg="Superusers users should have access to field 'ausgaben_merkmal'."
        )


class TestMemoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.MemoAdmin
    model = _models.Memorabilien
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestMusikerAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.MusikerAdmin
    model = _models.Musiker
    exclude_expected = ['genre', 'instrument', 'orte']
    fields_expected = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        cls.obj2 = make(
            cls.model, band__band_name=['Testband1', 'Testband2'],
            genre__genre=['Testgenre1', 'Testgenre2']
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('band_list', annotations)
        self.assertIsInstance(annotations['band_list'], Func)
        self.assertIn('genre_list', annotations)
        self.assertIsInstance(annotations['genre_list'], Func)
        self.assertIn('orte_list', annotations)
        self.assertIsInstance(annotations['orte_list'], Func)

    def test_band_string(self):
        obj = self.get_annotated_model_obj(self.obj2)
        self.assertEqual(self.model_admin.band_string(obj), 'Testband1, Testband2')

    def test_genre_string(self):
        obj = self.get_annotated_model_obj(self.obj2)
        self.assertEqual(self.model_admin.genre_string(obj), 'Testgenre1, Testgenre2')

    def test_orte_string(self):
        obj = self.get_annotated_model_obj(self.obj2)
        self.assertEqual(self.model_admin.orte_string(obj), '-')
        self.obj2.orte.add(make(_models.Ort, stadt='Dortmund', land__code='XYZ'))
        obj = self.get_annotated_model_obj(self.obj2)
        self.assertEqual(self.model_admin.orte_string(obj), 'Dortmund, XYZ')


class TestOrtAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.OrtAdmin
    model = _models.Ort
    fields_expected = ['stadt', 'land', 'bland']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_formfield_for_foreignkey_land_forwarded_to_bland(self):
        field = self.model._meta.get_field('bland')
        with patch("dbentry.admin.make_widget") as make_widget_mock:
            self.model_admin.formfield_for_foreignkey(field, self.get_request())
            make_widget_mock.assert_called_with(model=_models.Bundesland, forward=['land'])


class TestPersonAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.PersonAdmin
    model = _models.Person
    exclude_expected = ['orte']
    fields_expected = [
        'vorname', 'nachname', 'gnd_id', 'gnd_name', 'dnb_url',
        'beschreibung', 'bemerkungen'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, musiker__extra=1, autor__extra=1)
        # one extra 'empty' object without relations for Ist_Autor/Ist_Musiker:
        cls.obj2 = make(cls.model)
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('is_musiker', annotations)
        self.assertIsInstance(annotations['is_musiker'], Exists)
        self.assertIn('is_autor', annotations)
        self.assertIsInstance(annotations['is_autor'], Exists)
        self.assertIn('orte_list', annotations)
        self.assertIsInstance(annotations['orte_list'], Func)

    def test_is_musiker(self):
        obj1, obj2 = (
            self.queryset
            .annotate(**self.model.get_overview_annotations())
            .filter(id__in=[self.obj1.pk, self.obj2.pk])
            .order_by('id')
        )
        self.assertTrue(self.model_admin.is_musiker(obj1))
        self.assertFalse(self.model_admin.is_musiker(obj2))

    def test_is_autor(self):
        obj1, obj2 = (
            self.queryset
            .annotate(**self.model.get_overview_annotations())
            .filter(id__in=[self.obj1.pk, self.obj2.pk])
            .order_by('id')
        )
        self.assertTrue(self.model_admin.is_autor(obj1))
        self.assertFalse(self.model_admin.is_autor(obj2))

    def test_orte_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.orte_string(obj), '-')
        o = make(_models.Ort, stadt='Dortmund', land__code='XYZ')
        self.obj1.orte.add(o)
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.orte_string(obj), 'Dortmund, XYZ')


class TestPlakatAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.PlakatAdmin
    model = _models.Plakat
    fields_expected = [
        'titel', 'plakat_id', 'size', 'datum', 'reihe', 'copy_related',
        'beschreibung', 'bemerkungen'
    ]
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band',
        'musiker', 'ort', 'spielort', 'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, datum='2022-10-17')
        cls.band = make(_models.Band)
        cls.musiker = make(_models.Musiker)
        v1 = make(_models.Veranstaltung, name='Woodstock 1969', band=cls.band, musiker=cls.musiker)
        v2 = make(_models.Veranstaltung, name='Glastonbury 2004')
        cls.obj1.veranstaltung.set([v1, v2])
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('veranstaltung_list', annotations)
        self.assertIsInstance(annotations['veranstaltung_list'], Func)

    def test_datum_localized(self):
        self.obj1.refresh_from_db()
        with translation_override(language=None):
            self.assertEqual(self.model_admin.datum_localized(self.obj1), '17. October 2022')

    def test_veranstaltung_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(
            self.model_admin.veranstaltung_string(obj),
            'Glastonbury 2004, Woodstock 1969'
        )

    def test_copy_related_set(self):
        request = self.post_request(data={'copy_related': True})
        self.model_admin._copy_related(request, self.obj1)
        self.assertIn(self.band, self.obj1.band.all())
        self.assertIn(self.musiker, self.obj1.musiker.all())

    def test_get_fields_copy_related_removed_when_no_perms(self):
        """
        Assert that the 'copy_related' field is removed from the change form
        for users that lack change permission.
        """
        request = self.get_request(user=self.super_user)
        self.assertIn('copy_related', self.model_admin.get_fields(request))
        request = self.get_request(user=self.noperms_user)
        self.assertNotIn('copy_related', self.model_admin.get_fields(request))

    def test_save_related_calls_copy_related(self):
        """Assert that save_related calls _copy_related."""
        form_mock = Mock(instance=1)
        with patch('dbentry.admin.super'):
            with patch.object(self.model_admin, '_copy_related') as copy_related_mock:
                self.model_admin.save_related(
                    request=None,
                    form=form_mock,
                    formsets=None,
                    change=True
                )
                copy_related_mock.assert_called()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')

    def test_plakat_id(self):
        """Assert that plakat_id returns the id prefixed with a 'P' and padded with zeroes."""
        self.assertEqual(self.model_admin.plakat_id(self.obj1), f"P{self.obj1.pk:06}")


class TestSchlagwortAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.SchlagwortAdmin
    model = _models.Schlagwort
    fields_expected = ['schlagwort']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, schlagwort='Sub Schlagwort', schlagwortalias__alias=['Alias1', 'Alias2']
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('alias_list', annotations)
        self.assertIsInstance(annotations['alias_list'], Func)

    def test_alias_string(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.alias_string(obj), 'Alias1, Alias2')


class TestSpielortAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.SpielortAdmin
    model = _models.Spielort
    fields_expected = ['name', 'beschreibung', 'bemerkungen', 'ort']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestTechnikAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.TechnikAdmin
    model = _models.Technik
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestVeranstaltungAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VeranstaltungAdmin
    model = _models.Veranstaltung
    exclude_expected = ['genre', 'person', 'band', 'schlagwort', 'musiker']
    fields_expected = ['name', 'datum', 'spielort', 'reihe', 'beschreibung', 'bemerkungen']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, datum='2022-10-17',
            band__band_name='Led Zeppelin', musiker__kuenstler_name='Robert Plant'
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('kuenstler_list', annotations)
        self.assertIsInstance(annotations['kuenstler_list'], Func)

    def test_kuenstler_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.kuenstler_list(obj), 'Led Zeppelin, Robert Plant')

    def test_datum_localized(self):
        self.obj1.refresh_from_db()
        with translation_override(language=None):
            self.assertEqual(self.model_admin.datum_localized(self.obj1), '17. October 2022')


class TestVerlagAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VerlagAdmin
    model = _models.Verlag
    fields_expected = ['verlag_name', 'sitz']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model)
        super().setUpTestData()


class TestVideoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VideoAdmin
    model = _models.Video
    fields_expected = [
        'titel', 'laufzeit', 'jahr', 'quelle', 'original', 'release_id', 'discogs_url',
        'beschreibung', 'bemerkungen', 'medium', 'medium_qty'
    ]
    exclude_expected = [
        'band', 'genre', 'musiker', 'person', 'schlagwort', 'ort', 'spielort', 'veranstaltung']

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, band__band_name='Led Zeppelin', musiker__kuenstler_name='Robert Plant'
        )
        super().setUpTestData()

    def test_get_queryset_contains_annotations(self):
        """Assert that the queryset returned by get_queryset contains the expected annotations."""
        annotations = self.model_admin.get_queryset(self.get_request()).query.annotations
        self.assertIn('kuenstler_list', annotations)
        self.assertIsInstance(annotations['kuenstler_list'], Func)

    def test_kuenstler_list(self):
        obj = self.get_annotated_model_obj(self.obj1)
        self.assertEqual(self.model_admin.kuenstler_list(obj), 'Led Zeppelin, Robert Plant')

    def test_action_change_bestand(self):
        """Assert that the 'change_bestand' page can be navigated to from the changelist."""
        request_data = {
            'action': 'change_bestand',
            admin.helpers.ACTION_CHECKBOX_NAME: str(self.obj1.pk),
            'follow': True
        }
        with self.assertNotRaises(exceptions.FieldError):
            response = self.client.post(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/change_bestand.html')


class TestChangelistAnnotations(AdminTestCase):
    admin_site = miz_site
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(
            cls.model, status=_models.Ausgabe.Status.UNBEARBEITET,
            ausgabejahr__jahr=2022, ausgabenum__num=2
        )
        super().setUpTestData()

    def test_action_update(self):
        """
        Assert that actions can perform an update on a queryset sorted by an
        annotated field.
        """
        # queryset.update removes all annotations - which will cause a
        # FieldError when it's time to apply ordering that depends on an
        # annotated field.
        # See: https://code.djangoproject.com/ticket/28897
        # Fixed in django 4.1.
        request_data = {
            # 'index' specifies which action form (form to select an action from)
            # was used in case there are multiple such action forms
            # (i.e. at the top and the bottom)
            'index': '0',
            ACTION_CHECKBOX_NAME: str(self.obj.pk),
            'action': 'change_status_inbearbeitung',
        }
        # Order against one of the annotated fields:
        query_string = f"?o={self.model_admin.list_display.index('num_list') + 1}"
        self.client.post(self.changelist_path + query_string, data=request_data)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.status, _models.Ausgabe.Status.INBEARBEITUNG)

    def test_can_order_result_list(self):
        """Assert that the result list can be ordered against the annotated fields."""
        other = make(self.model, ausgabejahr__jahr=2022, ausgabenum__num=1)
        query_string = (
            # Need to apply some filters or the result list will be empty.
            "?ausgabejahr__jahr_0=2022&"
            f"o={self.model_admin.list_display.index('num_list') + 1}"
        )
        response = self.client.get(self.changelist_path + query_string)
        result_list = response.context_data['cl'].result_list
        self.assertIn('num_list', result_list.query.order_by)
        self.assertQuerysetEqual([other, self.obj], result_list)


class TestAuthAdminMixin(TestCase):

    @patch('dbentry.admin.super')
    def test_formfield_for_manytomany(self, mocked_super):
        """
        Assert that formfield_for_manytomany adds the model name to the
        human-readable part of the formfield's choices.
        """
        ct = contenttypes.models.ContentType.objects.get_for_model(_models.AusgabeLnum)
        perm_queryset = Permission.objects.filter(content_type=ct)
        mocked_formfield = Mock(queryset=perm_queryset)
        mocked_super.return_value = Mock(
            formfield_for_manytomany=Mock(return_value=mocked_formfield)
        )
        formfield = _admin.AuthAdminMixin().formfield_for_manytomany(None)
        for choice in formfield.choices:
            with self.subTest(choice=choice):
                self.assertIn(_models.AusgabeLnum.__name__, choice[1])


class TestMIZUserAdmin(AdminTestCase):
    admin_site = miz_site
    model = User
    model_admin_class = _admin.MIZUserAdmin

    def test_get_queryset_adds_activity_annotation(self):
        """
        Assert that get_queryset adds an annotation that shows the activity of
        users.
        """
        queryset = self.model_admin.get_queryset(self.get_request())
        self.assertIn('activity', queryset.query.annotations)
        self.assertEqual(queryset.get(pk=self.super_user.pk).activity, 0)
        LogEntry.objects.log_action(
            user_id=self.super_user.pk,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id=self.super_user.pk,
            object_repr=repr(self.super_user),
            action_flag=admin.models.CHANGE,
            change_message=[],
        )
        queryset = self.model_admin.get_queryset(self.get_request())
        self.assertEqual(queryset.get(pk=self.super_user.pk).activity, 1)

    def test_activity(self):
        """
        Assert that activity returns the value of the 'activity' attribute
        of the given user.
        """
        self.super_user.activity = 'Foo'
        self.assertEqual(self.model_admin.activity(self.super_user), 'Foo')


class TestMIZLogEntryAdmin(AdminTestCase):
    admin_site = miz_site
    model = LogEntry
    model_admin_class = _admin.MIZLogEntryAdmin

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj = LogEntry.objects.log_action(
            user_id=cls.super_user.pk,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id=cls.super_user.pk,
            object_repr="Superuser",
            action_flag=admin.models.CHANGE,
            change_message=[{
                'changed':
                    {'fields': ['username'], 'name': 'User', 'object': 'Superuser'}
            }],
        )

    def test_object(self):
        """Assert that the object method returns a link to the given object."""
        opts = User._meta
        url = reverse(
            f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_change",
            args=[self.super_user.pk]
        )
        self.assertEqual(self.model_admin.object(self.obj), f'<a href="{url}">Superuser</a>')

    def test_change_message_verbose(self):
        """
        Assert change_message_verbose returns the full change message of the
        given object.
        """
        with translation_override(language=None):
            self.assertEqual(
                self.model_admin.change_message_verbose(self.obj),
                "Changed username for User “Superuser”."
            )

    def test_change_message_raw(self):
        """
        Assert that change_message_raw returns the raw change message of the
        given object.
        """
        self.assertEqual(
            self.model_admin.change_message_raw(self.obj),
            '[{"changed": {"fields": ["username"], "name": "User", "object": "Superuser"}}]'
        )
