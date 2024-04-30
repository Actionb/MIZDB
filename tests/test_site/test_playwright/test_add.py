import pytest

from dbentry import models as _models
from tests.model_factory import make
from tests.test_site.test_playwright.conftest import ADD_VIEW, CRUD_MODELS

pytestmark = pytest.mark.e2e


def get_data_for_model(model):
    """Return form data for the given model."""
    # form field name attr: value
    data = {
        _models.Audio: {
            "titel": "Testaudio",
            "tracks": "2",
            "laufzeit": "144",
            "jahr": "2023",
        },
        _models.Ausgabe: {
            "status": _models.Ausgabe.Status.UNBEARBEITET,
            "sonderausgabe": True,
            "magazin": "Testmagazin",
            "beschreibung": "Testausgabe",
        },
        _models.Autor: {
            "person": "Alice",
            "kuerzel": "AT",
        },
        _models.Artikel: {
            "ausgabe__magazin": "Testmagazin",
            "ausgabe": "2022",
            "schlagzeile": "Testartikel",
            "seite": "22",
            "seitenumfang": _models.Artikel.Umfang.F,
            "zusammenfassung": "Dies ist ein Test.",
        },
        _models.Band: {
            "band_name": "Red Hot Chilli Peppers",
        },
        _models.Plakat: {
            "titel": "Testplakat",
            "size": "DINA3",
        },
        _models.Buch: {
            "titel": "Testbuch",
            "is_buchband": True,
            "seitenumfang": "120",
            "jahr": "1999",
            "EAN": "9783453319448",
            "ISBN": "9783453319448",
        },
        _models.Genre: {
            "genre": "Testgenre",
        },
        _models.Magazin: {
            "magazin_name": "Testmagazin",
            "fanzine": True,
            "issn": "0035-791X",
        },
        _models.Musiker: {
            "kuenstler_name": "Testkünstler",
            "person": "Alice",
        },
        _models.Person: {
            "vorname": "Bob",
            "nachname": "Testman",
        },
        _models.Schlagwort: {
            "schlagwort": "Testschlagwort",
        },
        _models.Spielort: {
            "name": "Testspielort",
            "ort": "Dortmund",
        },
        _models.Veranstaltung: {
            "name": "Testveranstaltung",
            "datum_0": "2023",
            "datum_1": "10",
            "datum_2": "19",
            "spielort": "Testspielort",
        },
        _models.Herausgeber: {
            "herausgeber": "Testherausgeber",
        },
        _models.Instrument: {
            "instrument": "Testinstrument",
            "kuerzel": "TI",
        },
        _models.Verlag: {
            "verlag_name": "Testverlag",
            "sitz": "Dortmund",
        },
        _models.Video: {
            "titel": "Testvideo",
            "laufzeit": "144",
            "jahr": "2022",
            "quelle": "live",
            "discogs_url": "https://www.discogs.com/release/388395-Black-Rebel-Motorcycle-Club-BRMC",
        },
        _models.Ort: {
            "stadt": "Teststadt",
            "land": "Deutschland",
            "bland": "Nordrhein",
        },
        _models.Land: {
            "land_name": "Testland",
            "code": "TE",
        },
        _models.Bundesland: {
            "bland_name": "Testbundesland",
            "code": "TBL",
            "land": "Deutschland",
        },
        _models.Brochure: {
            "titel": "Testbroschüre",
            "zusammenfassung": "Dies it ein Test.",
        },
        _models.Katalog: {
            "titel": "Testkatalog",
            "zusammenfassung": "Dies it ein Test.",
            "art": _models.Katalog.Types.TON,
        },
        _models.Kalender: {
            "titel": "Testkalender",
            "zusammenfassung": "Dies it ein Test.",
        },
        _models.Foto: {
            "titel": "Testfoto",
            "size": "34x22",
            "datum_0": "1969",
            "typ": _models.Foto.Types.REPRINT,
            "farbe": True,
        },
        _models.Plattenfirma: {
            "name": "Testfirma",
        },
        _models.Lagerort: {
            "ort": "Hier",
            "raum": "101",
            "regal": "Regal 2",
        },
        _models.Geber: {
            "name": "Bob",
        },
        _models.Provenienz: {
            "typ": _models.Provenienz.Types.SPENDE,
            "geber": "Testgeber",
        },
        _models.Schriftenreihe: {
            "name": "Testreihe",
        },
        _models.Bildreihe: {
            "name": "Testreihe",
        },
        _models.Veranstaltungsreihe: {
            "name": "Testreihe",
        },
        _models.VideoMedium: {
            "medium": "Testmedium",
        },
        _models.AudioMedium: {
            "medium": "Testmedium",
        },
    }
    return data.get(model, None)


@pytest.fixture
def test_data():
    magazin = make(_models.Magazin, magazin_name="Testmagazin")
    ausgabe = make(_models.Ausgabe, magazin=magazin, ausgabejahr__jahr=2022, ausgabenum__num=1)
    person = make(_models.Person, vorname="Alice", nachname="Testman")
    land = make(_models.Land, land_name="Deutschland", code="de")
    bland = make(_models.Bundesland, bland_name="Nordrhein-Westfalen", code="NRW", land=land)
    ort = make(_models.Ort, stadt="Dortmund", land=land, bland=bland)
    spielort = make(_models.Spielort, name="Testspielort", ort=ort)
    geber = make(_models.Geber, name="Testgeber")
    return {
        _models.Magazin: magazin,
        _models.Ausgabe: ausgabe,
        _models.Person: person,
        _models.Land: land,
        _models.Bundesland: bland,
        _models.Ort: ort,
        _models.Spielort: spielort,
        _models.Geber: geber,
    }


@pytest.mark.parametrize("model", CRUD_MODELS)
@pytest.mark.parametrize("view_name", [ADD_VIEW])
@pytest.mark.usefixtures("login_superuser")
@pytest.mark.usefixtures("test_data")
def test_can_add(page, view_name, model, fill_value):
    """Assert that the add view can be used to add new model objects."""
    model_data = get_data_for_model(model)
    assert model_data, f"No test data for model '{model}'"
    count = model.objects.count()
    for field_name, value in model_data.items():
        fill_value(field_name, value)
    with page.expect_request_finished():
        page.get_by_role("button", name="Sichern", exact=True).click()
    assert count + 1 == model.objects.count(), "Model object was not added"
