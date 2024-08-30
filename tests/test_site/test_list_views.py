"""Tests for the (change)list views."""

import json
from unittest.mock import Mock, patch

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View

from dbentry import models as _models
from dbentry.site.registry import ModelType, Registry, register_changelist
from dbentry.site.views import list
from dbentry.site.views.base import ORDER_VAR
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
        response = list.changelist_selection_sync(request)
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
    view_class = list.Index

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
    view_class = list.AudioList


class TestAusgabeList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.AusgabeList

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
    view_class = list.AutorList


class TestArtikelList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.ArtikelList


class TestBandList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.BandList


class TestPlakatList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.PlakatList


class TestBuchList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.BuchList


class TestGenreList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.GenreList


class TestMagazinList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.MagazinList


class TestMusikerList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.MusikerList

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.band = band = make(_models.Band)
        cls.found = make(_models.Musiker, band=band)
        cls.not_found = make(_models.Musiker)

    def test_search_form_bands(self):
        """Assert that the user can filter the changelist by Bands."""
        response = self.get_response(reverse("dbentry_musiker_changelist"), data={"band": self.band.pk})
        results = [r for r, _ in response.context_data["result_rows"]]
        self.assertIn(self.found, results)
        self.assertNotIn(self.not_found, results)


class TestPersonList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.PersonList


class TestSchlagwortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.SchlagwortList


class TestSpielortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.SpielortList


class TestVeranstaltungList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.VeranstaltungList


class TestVerlagList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.VerlagList


class TestVideoList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.VideoList


class TestOrtList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.OrtList


class TestInstrumentList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.InstrumentList


class TestHerausgeberList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.HerausgeberList


class TestBrochureList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.BrochureList


class TestKatalogList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.WarenkatalogList


class TestKalenderList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.ProgrammheftList


class TestFotoList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.FotoList


class TestPlattenfirmaList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.PlattenfirmaList


class TestLagerortList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.LagerortList


class TestGeberList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.GeberList


class TestProvenienzList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.ProvenienzList


class TestSchriftenreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.SchriftenreiheList


class TestBildreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.BildreiheList


class TestVeranstaltungsreiheList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.VeranstaltungsreiheList


class TestVideoMediumList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.VideoMediumList


class TestAudioMediumList(ListViewTestMethodsMixin, ListViewTestCase):
    view_class = list.AudioMediumList
