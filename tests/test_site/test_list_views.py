"""Tests for the (change)list views."""

import json
from unittest.mock import Mock, patch

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, NoReverseMatch
from django.utils.http import urlencode
from django.views import View

from dbentry import models as _models
from dbentry.site.registry import ModelType, Registry, register_changelist
from dbentry.site.views import list as list_views
from dbentry.site.views.base import ORDER_VAR, IMPROVABLE_QUERY_PARAM
from dbentry.site.views.list import _get_continue_url
from tests.case import DataTestCase, RequestTestCase, ViewTestCase
from tests.model_factory import make
from tests.test_site.models import Band, Genre, Musician


class TestChangelistSelectionSync(DataTestCase, RequestTestCase):
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)
        super().setUpTestData()

    def test_changelist_selection_sync(self):
        selected = json.dumps([str(self.obj.pk), "-1"])
        opts = self.model._meta
        request = self.get_request(data={"model": f"{opts.app_label}.{opts.model_name}", "ids": selected})
        response = list_views.changelist_selection_sync(request)
        data = json.loads(response.content)
        self.assertEqual(data["remove"], ["-1"])


@patch("dbentry.site.views.list.get_change_url")
class TestIndexFuncs(RequestTestCase):
    """Test functions that the IndexView is using."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.band = make(_models.Band)
        cls.artikel = make(_models.Artikel)

    def test_get_continue_url(self, get_url_mock):
        get_url_mock.return_value = "Band URL"
        self.assertEqual(_get_continue_url(self.get_request(), self.band), "Band URL")
        get_url_mock.assert_called()

    @patch("dbentry.site.views.list.add_preserved_filters")
    def test_get_continue_url_artikel(self, add_filters_mock, get_url_mock):
        get_url_mock.return_value = "Artikel URL"
        _get_continue_url(self.get_request(), self.artikel)
        add_filters_mock.assert_called()
        _, kwargs = add_filters_mock.call_args
        filters = f"ausgabe__magazin={self.artikel.ausgabe.magazin.pk}&ausgabe={self.artikel.ausgabe.pk}"
        expected_context = {
            "opts": self.artikel._meta,
            "preserved_filters": urlencode({"_changelist_filters": filters}),
        }
        self.assertEqual(kwargs["base_url"], "Artikel URL")
        self.assertEqual(kwargs["context"], expected_context)


test_site = Registry()


@register_changelist([Band, Musician], category=ModelType.ARCHIVGUT, site=test_site)
class ChangelistView(View):
    pass


class TestIndex(ViewTestCase):
    view_class = list_views.Index

    @classmethod
    def add_log(cls, obj, action_flag):
        return LogEntry.objects.log_action(
            user_id=cls.super_user.pk,
            content_type_id=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
            object_repr="Band 1",
            action_flag=action_flag,
        )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.band1 = band1 = make(Band, name="Band 1")
        cls.band2 = band2 = make(Band, name="Band 2")
        deleted = make(Musician, name="Deleted")
        # Model Genre is not registered as category 'Archivgut', so logs for
        # that should not show up in 'last edits'
        genre = make(Genre)

        cls.add_log(band1, ADDITION)
        cls.band1_log = cls.add_log(band1, CHANGE)
        cls.band2_log = cls.add_log(band2, ADDITION)

        cls.add_log(deleted, ADDITION)
        cls.add_log(deleted, DELETION)
        deleted.delete()

        cls.add_log(genre, ADDITION)

    def get_descriptions(self):
        """
        Return the object description strings of the tuples in the 'last_edits'
        context item list.
        """
        view = self.get_view(self.get_request(), site=test_site)
        with patch("dbentry.site.views.list.super") as super_mock:
            with patch("dbentry.site.views.list._get_continue_url", new=Mock(return_value="")):
                super_mock.return_value.get_context_data.return_value = {}
                last_edits = view.get_context_data()["last_edits"]
        return [e[1] for e in last_edits]

    def test_get_context_data_last_edits(self):
        """Assert that the last edits contain the expected descriptions."""
        descriptions = self.get_descriptions()
        for expected_descr in ["Band: Band 2", "Band: Band 1"]:
            with self.subTest(expected_descr=expected_descr):
                self.assertIn(expected_descr, descriptions)
                descriptions.pop(descriptions.index(expected_descr))
        self.assertFalse(descriptions, msg="last edits contains unexpected additional items")

    def test_get_context_data_last_edits_no_duplicates(self):
        """Assert that last edits does not contain duplicates."""
        self.assertEqual(self.get_descriptions().count("Band: Band 1"), 1)

    def test_get_context_data_last_edits_no_deleted(self):
        """Assert that deleted objects do not appear in the last edits."""
        self.assertNotIn("Musician: Deleted", self.get_descriptions())

    def test_get_improvable_views(self):
        """Assert that get_improvable_views adds the expected changelist URLs."""
        view = self.get_view(self.get_request(), site=test_site)
        # Ignore the descriptions returned by get_improvable views:
        improvable_views = [(url, verbose_name) for url, verbose_name, _ in view.get_improvable_views()]

        expected = [
            (f"/artikel/?{IMPROVABLE_QUERY_PARAM}=1", "Artikel"),
            (f"/band/?{IMPROVABLE_QUERY_PARAM}=1", "Bands"),
            (f"/musiker/?{IMPROVABLE_QUERY_PARAM}=1", "Musiker"),
        ]
        for expected_url, label in expected:
            with self.subTest(label=label):
                self.assertIn((expected_url, label), improvable_views)

    def test_get_improvable_views_no_reverse_match(self):
        """
        Assert that get_improvable_views catches and suppresses NoReverseMatch
        exceptions.
        """
        view = self.get_view(self.get_request(), site=test_site)
        with patch("dbentry.site.views.list.reverse") as reverse_mock:
            reverse_mock.side_effect = NoReverseMatch
            self.assertFalse(view.get_improvable_views())


class ListViewTestCase(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        # Add a model object for the list display stuff.
        cls.obj = make(cls.view_class.model)
        super().setUpTestData()

    @property
    def url_name(self):
        return f"{self.view_class.model._meta.app_label}_{self.view_class.model._meta.model_name}"

    @property
    def url(self):
        return reverse(f"{self.url_name}_changelist")


class ListViewTestMethodsMixin:
    """Test methods shared by ListView tests."""

    def test_available(self: ListViewTestCase):
        """Assert that the view is available and returns an OK response."""
        response = self.get_response(self.url)
        assert response.status_code == 200


class TestAudioList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.AudioList


class TestAusgabeList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.AusgabeList

    def test_ordered_chronologically(self):
        """Assert that the changelist queryset is ordered chronologically."""
        request = self.get_request(self.url)
        view = self.get_view(request)
        self.assertTrue(view.get_queryset().chronologically_ordered)

    def test_ordered_chronologically_filtered(self):
        """Assert that the filtered changelist queryset is ordered chronologically."""
        request = self.get_request(self.url, data={"magazin_id": self.obj.magazin_id})
        view = self.get_view(request)
        self.assertTrue(view.get_queryset().chronologically_ordered)

    def test_not_chronologically_ordered_if_order_params(self):
        """
        Assert that the changelist queryset is not ordered chronologically if
        an ordering was specified in the request parameters.
        """
        request = self.get_request(self.url, data={ORDER_VAR: "1"})
        view = self.get_view(request)
        self.assertFalse(view.get_queryset().chronologically_ordered)


class TestAutorList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.AutorList


class TestArtikelList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.ArtikelList

    def test_filter_improvable(self):
        """Assert that filter_improvable only shows objects that lack data."""
        self.obj.delete()
        make(_models.Artikel, zusammenfassung="A proper summary!")
        improvable = make(_models.Artikel)
        improvable_w_dashes = make(_models.Artikel, schlagzeile="----")
        improvable_w_dots = make(_models.Artikel, schlagzeile=".....")

        view = self.get_view(self.get_request(path=f"{self.url}?{IMPROVABLE_QUERY_PARAM}=1"))
        queryset = view.filter_improvable(_models.Artikel.objects.all())
        self.assertEqual(queryset.count(), 3, msg=queryset)
        self.assertIn(improvable, queryset)
        self.assertIn(improvable_w_dashes, queryset)
        self.assertIn(improvable_w_dots, queryset)


class TestBandList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.BandList

    def test_filter_improvable(self):
        """Assert that filter_improvable only shows objects that lack data."""
        self.obj.delete()
        make(_models.Band, band_name="has_beschreibung", beschreibung="foo")
        make(_models.Band, band_name="has_urls", musiker__extra=1)
        make(_models.Band, band_name="has_genre", genre__extra=1)
        make(_models.Band, band_name="has_alias", bandalias__extra=1)
        make(_models.Band, band_name="has_musiker", musiker__extra=1)
        make(_models.Band, band_name="has_orte", orte__extra=1)
        improvable = make(_models.Band, band_name="improvable")

        view = self.get_view(self.get_request(path=f"{self.url}?{IMPROVABLE_QUERY_PARAM}=1"))
        queryset = view.filter_improvable(_models.Band.objects.all())
        self.assertEqual(queryset.count(), 1, msg=queryset)
        self.assertIn(improvable, queryset)


class TestPlakatList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.PlakatList


class TestBuchList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.BuchList


class TestGenreList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.GenreList


class TestMagazinList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.MagazinList


class TestMusikerList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.MusikerList

    def test_search_form_bands(self):
        """Assert that the user can filter the changelist by Bands."""
        self.band = band = make(_models.Band)
        self.found = make(_models.Musiker, band=band)
        self.not_found = make(_models.Musiker)
        response = self.get_response(reverse("dbentry_musiker_changelist"), data={"band": self.band.pk})
        results = [r for r, _ in response.context_data["result_rows"]]
        self.assertIn(self.found, results)
        self.assertNotIn(self.not_found, results)

    def test_filter_improvable(self):
        """Assert that filter_improvable only shows objects that lack data."""
        self.obj.delete()
        make(_models.Musiker, kuenstler_name="has_beschreibung", beschreibung="foo")
        make(_models.Musiker, kuenstler_name="has_urls", urls__extra=1)
        make(_models.Musiker, kuenstler_name="has_genre", genre__extra=1)
        make(_models.Musiker, kuenstler_name="has_alias", musikeralias__extra=1)
        make(_models.Musiker, kuenstler_name="has_musiker", band__extra=1)
        make(_models.Musiker, kuenstler_name="has_orte", orte__extra=1)
        improvable = make(_models.Musiker, kuenstler_name="improvable")

        view = self.get_view(self.get_request(path=f"{self.url}?{IMPROVABLE_QUERY_PARAM}=1"))
        queryset = view.filter_improvable(_models.Musiker.objects.all())
        self.assertEqual(queryset.count(), 1, msg=queryset)
        self.assertIn(improvable, queryset)


class TestPersonList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.PersonList


class TestSchlagwortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.SchlagwortList


class TestSpielortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.SpielortList


class TestVeranstaltungList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.VeranstaltungList


class TestVerlagList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.VerlagList


class TestVideoList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.VideoList


class TestOrtList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.OrtList


class TestInstrumentList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.InstrumentList


class TestHerausgeberList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.HerausgeberList


class TestBrochureList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.BrochureList


class TestKatalogList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.WarenkatalogList


class TestKalenderList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.ProgrammheftList


class TestFotoList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.FotoList


class TestPlattenfirmaList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.PlattenfirmaList


class TestLagerortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.LagerortList


class TestGeberList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.GeberList


class TestProvenienzList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.ProvenienzList


class TestSchriftenreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.SchriftenreiheList


class TestBildreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.BildreiheList


class TestVeranstaltungsreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.VeranstaltungsreiheList


class TestVideoMediumList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.VideoMediumList


class TestAudioMediumList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list_views.AudioMediumList
