"""Tests for the (change)list views."""
import json

from django.urls import reverse

from dbentry.site.views import list
from tests.case import ViewTestCase, RequestTestCase, DataTestCase
from tests.model_factory import make
from tests.test_site.models import Band


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
