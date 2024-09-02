"""Tests for the edit views."""

from unittest.mock import patch
from urllib.parse import unquote

from django.forms import ModelChoiceField
from django.urls import NoReverseMatch, reverse

from dbentry import models as _models
from dbentry.site.views import edit
from tests.case import ViewTestCase
from tests.model_factory import make


class EditViewTestCase(ViewTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.view_class.model)
        super().setUpTestData()

    @property
    def url_name(self):
        return f"{self.view_class.model._meta.app_label}_{self.view_class.model._meta.model_name}"

    @property
    def add_url(self):
        try:
            return reverse(f"{self.url_name}_add")
        except NoReverseMatch as e:
            self.fail(f"Add URL not available - did you forget to register the view? {e}")

    @property
    def edit_url(self):
        try:
            return unquote(reverse(self.url_name + "_change", args=["{pk}"]))
        except NoReverseMatch as e:
            self.fail(f"Edit URL not available - did you forget to register the view? {e}")

    @property
    def view_url(self):
        try:
            return unquote(reverse(self.url_name + "_view", args=["{pk}"]))
        except NoReverseMatch as e:
            self.fail(f"View URL not available - did you forget to register the view? {e}")

    def get_edit_view(self, obj, request=None):
        if request is None:
            request = self.get_request(self.edit_url.format(pk=obj.pk))
        return self.get_view(request, extra_context={"add": False}, kwargs={self.view_class.pk_url_kwarg: str(obj.pk)})

    def get_form_data(self):
        """Return minimal required data for the view's form and formsets."""
        data = {}
        view = self.view_class(extra_context={"add": True})
        form = view.get_form_class()()
        for name, field in form.fields.items():
            if not field.required:
                continue
            if isinstance(field, ModelChoiceField):
                value = make(field.queryset.model).pk
            else:
                value = "0"
            data[form.add_prefix(name)] = value
        data.update(self.management_form_data())
        data["_continue"] = ""  # save button
        return data

    def management_form_data(self):
        """Return minimal required data dict for the management forms."""
        data = {}
        view = self.view_class(extra_context={"add": True})
        formsets = [fs() for fs in view.get_formset_classes()]
        for formset in formsets:
            for name, field in formset.management_form.fields.items():
                if field.required:
                    data[formset.add_prefix(name)] = "0"
        return data


class EditViewTestMethodsMixin:
    """Test methods shared by EditView tests."""

    def test_available(self: EditViewTestCase):
        """Assert that the view is available and returns an OK response."""
        for url in (self.add_url, self.edit_url, self.view_url):
            url = url.format(pk=self.obj.pk)
            with self.subTest(url=url):
                response = self.get_response(url)
                assert response.status_code == 200

    def test_can_add(self: EditViewTestCase):
        """Assert that objects can be added via POST request."""
        response = self.post_response(self.add_url, data=self.get_form_data(), follow=True)
        assert response.status_code == 200

    def test_can_edit(self: EditViewTestCase):
        """Assert that objects can be edited via POST request."""
        response = self.post_response(self.edit_url.format(pk=self.obj.pk), data=self.get_form_data(), follow=True)
        assert response.status_code == 200


class TestAudioView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.AudioView

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ausgabe1 = ausgabe1 = make(_models.Ausgabe)
        cls.ausgabe2 = ausgabe2 = make(_models.Ausgabe)
        cls.obj.ausgabe_set.add(ausgabe1, ausgabe2)

    def test_ausgabe_inline_contains_magazin_data(self):
        """
        Assert that the forms of the AusgabeInline include initial data for the
        magazin field.
        """
        with patch.object(self.view_class, "inlines", new=[self.view_class.AusgabeInline]):
            response = self.get_response(self.edit_url.format(pk=self.obj.pk))
            formset = response.context_data["inlines"][0][0]
            self.assertEqual(formset.forms[0].initial["ausgabe__magazin"], self.ausgabe1.magazin)
            self.assertEqual(formset.forms[1].initial["ausgabe__magazin"], self.ausgabe2.magazin)


class TestAusgabeView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.AusgabeView

    def test_name_updated_after_save(self):
        """Assert that the (computed) name is up-to-date after a save."""
        obj = make(self.view_class.model, ausgabejahr__jahr=["2002"], ausgabenum__num=["1"])
        url = self.edit_url.format(pk=obj.pk)
        data = {
            "_continue": "",
            "magazin": obj.magazin_id,
            "status": "unb",
            # Number inline form data:
            "ausgabenum_set-TOTAL_FORMS": "1",
            "ausgabenum_set-INITIAL_FORMS": "1",
            "ausgabenum_set-0-num": "2",  # change the number from 1 to 2
            "ausgabenum_set-0-ausgabe": obj.pk,
            "ausgabenum_set-0-id": obj.ausgabenum_set.all().first().pk,
            # Management forms of the other inlines:
            "ausgabemonat_set-TOTAL_FORMS": "0",
            "ausgabemonat_set-INITIAL_FORMS": "0",
            "ausgabelnum_set-TOTAL_FORMS": "0",
            "ausgabelnum_set-INITIAL_FORMS": "0",
            "ausgabejahr_set-TOTAL_FORMS": "0",
            "ausgabejahr_set-INITIAL_FORMS": "0",
            "Ausgabe_audio-TOTAL_FORMS": "0",
            "Ausgabe_audio-INITIAL_FORMS": "0",
            "Ausgabe_video-TOTAL_FORMS": "0",
            "Ausgabe_video-INITIAL_FORMS": "0",
            "bestand_set-TOTAL_FORMS": "0",
            "bestand_set-INITIAL_FORMS": "0",
        }
        response = self.post_response(url, data=data, follow=True)
        self.assertEqual(str(response.context_data["object"]), "2002-02")


class TestAutorView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.AutorView


class TestArtikelView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.ArtikelView


class TestBandView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.BandView


class TestPlakatView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.PlakatView


class TestBuchView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.BuchView


class TestGenreView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.GenreView

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        obj = cls.obj  # noqa
        cls.brochure = make(_models.Brochure, genre=obj)
        cls.kalender = make(_models.Kalender, genre=obj)
        cls.katalog = make(_models.Katalog, genre=obj)

    def test_get_changelist_links_contains_brochure_models(self):
        """
        Assert that the changelist links can contain links to the three
        Brochure models (Brochure, Kalender, Katalog).
        """
        # Links to these models were unavailable since
        # get_changelist_url_for_relation resolves the relation to the abstract
        # BaseBrochure model (instead of the concrete child models) which does
        # not have a view and thus no URL.
        expected_urls = [
            (model, reverse(f"dbentry_{model._meta.model_name}_changelist") + f"?genre={self.obj.pk}")
            for model in (_models.Brochure, _models.Kalender, _models.Katalog)
        ]

        view = self.get_edit_view(self.obj)
        view.object = self.obj
        urls = [url for url, *_ in view.get_changelist_links()]
        for model, expected_url in expected_urls:
            with self.subTest(model=model):
                self.assertIn(expected_url, urls)


class TestMagazinView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.MagazinView


class TestMusikerView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.MusikerView


class TestPersonView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.PersonView


class TestSchlagwortView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.SchlagwortView


class TestSpielortView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.SpielortView


class TestVeranstaltungView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.VeranstaltungView


class TestVerlagView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.VerlagView


class TestVideoView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.VideoView

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ausgabe1 = ausgabe1 = make(_models.Ausgabe)
        cls.ausgabe2 = ausgabe2 = make(_models.Ausgabe)
        cls.obj.ausgabe_set.add(ausgabe1, ausgabe2)

    def test_ausgabe_inline_contains_magazin_data(self):
        """
        Assert that the forms of the AusgabeInline include initial data for the
        magazin field.
        """
        with patch.object(self.view_class, "inlines", new=[self.view_class.AusgabeInline]):
            response = self.get_response(self.edit_url.format(pk=self.obj.pk))
            formset = response.context_data["inlines"][0][0]
            self.assertEqual(formset.forms[0].initial["ausgabe__magazin"], self.ausgabe1.magazin)
            self.assertEqual(formset.forms[1].initial["ausgabe__magazin"], self.ausgabe2.magazin)


class TestOrtView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.OrtView


class TestInstrumentView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.InstrumentView


class TestHerausgeberView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.HerausgeberView


class TestBrochureView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.BrochureView


class TestKatalogView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.KatalogView


class TestKalenderView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.KalenderView


class TestFotoView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.FotoView


class TestPlattenfirmaView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.PlattenfirmaView


class TestLagerortView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.LagerortView


class TestGeberView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.GeberView


class TestProvenienzView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.ProvenienzView


class TestSchriftenreiheView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.SchriftenreiheView


class TestBildreiheView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.BildreiheView


class TestVeranstaltungsreiheView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.VeranstaltungsreiheView


class TestVideoMediumView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.VideoMediumView


class TestAudioMediumView(EditViewTestMethodsMixin, EditViewTestCase):
    view_class = edit.AudioMediumView
