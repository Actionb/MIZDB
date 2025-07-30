import pytest

from dbentry import models as _models
from tests.test_site.test_playwright.conftest import CHANGE_VIEW, CRUD_MODELS

pytestmark = pytest.mark.e2e


def get_data_for_model(model):
    """Return form data for the given model."""
    # form field name attr: value
    data = {
        _models.Audio: {"titel": "Testaudio"},
        _models.Ausgabe: {"beschreibung": "Testausgabe"},
        _models.Autor: {"kuerzel": "AT"},
        _models.Artikel: {"schlagzeile": "Testartikel"},
        _models.Band: {"band_name": "Red Hot Chilli Peppers"},
        _models.Plakat: {"titel": "Testplakat"},
        _models.Buch: {"titel": "Testbuch"},
        _models.Genre: {"genre": "Testgenre"},
        _models.Magazin: {"magazin_name": "Testmagazin"},
        _models.Musiker: {"kuenstler_name": "Testkünstler"},
        _models.Person: {"nachname": "Testman"},
        _models.Schlagwort: {"schlagwort": "Testschlagwort"},
        _models.Spielort: {"name": "Testspielort"},
        _models.Veranstaltung: {"name": "Testveranstaltung"},
        _models.Herausgeber: {"herausgeber": "Testherausgeber"},
        _models.Instrument: {"instrument": "Testinstrument"},
        _models.Verlag: {"verlag_name": "Testverlag"},
        _models.Video: {"titel": "Testvideo"},
        _models.Ort: {"stadt": "Teststadt"},
        _models.Land: {"land_name": "Testland"},
        _models.Bundesland: {"bland_name": "Testbundesland"},
        _models.Brochure: {"titel": "Testbroschüre"},
        _models.Katalog: {"titel": "Testkatalog"},
        _models.Kalender: {"titel": "Testkalender"},
        _models.Foto: {"titel": "Testfoto"},
        _models.Plattenfirma: {"name": "Testfirma"},
        _models.Lagerort: {"ort": "Testlagerort"},
        _models.Geber: {"name": "Bob"},
        _models.Provenienz: {"typ": _models.Provenienz.Types.FUND},
        _models.Schriftenreihe: {"name": "Testreihe"},
        _models.Bildreihe: {"name": "Testreihe"},
        _models.Veranstaltungsreihe: {"name": "Testreihe"},
        _models.VideoMedium: {"medium": "Testmedium"},
        _models.AudioMedium: {"medium": "Testmedium"},
        _models.Memorabilien: {"titel": "Test Memorabilie"},
        _models.MemoTyp: {"name": "Test MemoTyp"},
    }
    return data.get(model, None)


@pytest.mark.parametrize("model", CRUD_MODELS)
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_can_edit(page, view_name, test_object, model, fill_value):
    """Assert that the change view can be used to edit model objects."""
    model_data = get_data_for_model(model)
    assert model_data, f"No change data for model '{model}'"
    before = str(test_object)
    for field_name, value in model_data.items():
        fill_value(field_name, value)
    with page.expect_response(lambda r: True) as response_info:
        page.get_by_role("button", name="Sichern", exact=True).click()
    assert response_info.value.status != 500
    if "Änderungen bestätigen" in page.title():
        # Some views may require confirmation.
        page.get_by_text("Ja, ich bin sicher").click()
    test_object.refresh_from_db()
    after = str(test_object)
    assert after != before, "Model object was not changed."
