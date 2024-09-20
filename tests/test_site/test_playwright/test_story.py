import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.model_factory import make

pytestmark = pytest.mark.e2e


@pytest.fixture
def beatles():
    return make(_models.Band, band_name="The Beatles")


@pytest.fixture
def paul():
    return make(_models.Musiker, kuenstler_name="Paul McCartney")


@pytest.fixture
def magazin():
    return make(_models.Magazin, magazin_name="Testmagazin")


@pytest.fixture
def ausgabe(magazin):
    return make(_models.Ausgabe, magazin=magazin, ausgabejahr__jahr="2022", ausgabenum__num="2")


@pytest.fixture
def dropdown():
    """Return the dropdown div for the given TomSelect ts-control div."""

    def inner(ts_control):
        elem = ts_control.locator(":scope ~ div")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def dropdown_input(dropdown):
    """Return the dropdown input element for the given TomSelect element."""

    def inner(ts_control):
        elem = dropdown(ts_control).locator(".dropdown-input")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def selected_items(dropdown):
    """Return a locator for the selected items of the given TomSelect element."""

    def inner(ts_control):
        elem = ts_control.locator(".item")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.mark.parametrize("view_name", ["index"])
@pytest.mark.usefixtures("superuser", "beatles", "paul", "magazin", "ausgabe")
def test_story_create_artikel(context, page, view_name, dropdown, dropdown_input, selected_items):
    """Simulate the workflow of creating a full Artikel object."""
    # The user logs in after landing on the index page:
    page.get_by_role("button", name="Anmelden").click()
    page.get_by_role("link", name="Anmelden").click()
    page.wait_for_url("**/login/")
    page.get_by_label("Benutzername").fill("admin")
    page.get_by_label("Passwort").fill("admin")
    page.get_by_role("button", name="Anmelden").click()
    page.wait_for_url(re.compile(""))
    expect(page).to_have_title(re.compile("Index"))

    # Go to the Artikel changelist, and search for Artikel objects of a
    # certain Ausgabe object:
    page.get_by_role("link", name="Artikel").click()
    page.wait_for_url("**/artikel/")
    page.get_by_role("button", name="Erweiterte Suchoptionen anzeigen").click()
    ts_control = page.locator("#id_ausgabe__magazin-ts-control")
    ts_control.click()
    with page.expect_request_finished():
        dropdown_input(ts_control).fill("Testmagazin")
    dropdown(ts_control).get_by_text("Testmagazin").click()
    ts_control = page.locator("#id_ausgabe-ts-control")
    ts_control.click()
    with page.expect_request_finished():
        dropdown_input(ts_control).fill("2022")
    dropdown(ts_control).get_by_text("2022-02").click()
    page.get_by_role("button", name="Suchen").click()
    page.wait_for_url("**/artikel/**")

    # Add a new Artikel:
    page.get_by_role("link", name=re.compile("hinzufügen", re.IGNORECASE)).first.click()
    page.wait_for_url("**/artikel/add/**")
    # Magazin and Ausgabe field should already contain data:
    items = selected_items(page.locator("#id_ausgabe__magazin-ts-control"))
    expect(items.get_by_text("Testmagazin")).to_be_visible()
    items = selected_items(page.locator("#id_ausgabe-ts-control"))
    expect(items.get_by_text("2022-02")).to_be_visible()
    # Add data:
    page.get_by_label("Schlagzeile").fill("Testartikel")
    page.get_by_label("Seite", exact=True).fill("22")
    # Add the band:
    page.get_by_role("tab", name=re.compile("Bands")).click()
    tab_pane = page.locator("#artikel_band-tab-pane")
    ts_control = tab_pane.locator("#id_Artikel_band-0-band-ts-control")
    ts_control.click()  # open dropdown
    input_elem = dropdown_input(ts_control)
    with page.expect_request_finished():
        input_elem.fill("Beatles")
    tab_pane.get_by_text("The Beatles").click()

    # User saves the object:
    page.get_by_role("button", name="Sichern und weiterbearbeiten").click()
    page.wait_for_url(re.compile(r".*\/artikel\/\d+\/change\/.*"))
    # The members tab should have been updated:
    page.get_by_role("tab", name="Bands 1")

    # Edit the band from within the inline:
    page.get_by_role("tab", name=re.compile("Bands")).click()
    ts_control = tab_pane.locator("#id_Artikel_band-0-band-ts-control")
    band = selected_items(ts_control).first
    with context.expect_page() as new_page_info:
        band.get_by_title("Bearbeiten").click()
    band_popup = new_page_info.value
    band_popup.wait_for_load_state()

    # Add two new members to the band:
    band_popup.get_by_role("tab", name=re.compile("Band-Mitglieder")).click()
    tab_pane = band_popup.locator("#band_musiker-tab-pane")
    ts_control = tab_pane.locator("#id_Band_musiker-0-musiker-ts-control")
    ts_control.click()  # open dropdown
    input_elem = dropdown_input(ts_control)
    expect(input_elem).to_be_focused()
    with band_popup.expect_request_finished():
        input_elem.fill("McCartney")
    tab_pane.get_by_text("Paul McCartney").click()

    # Add a member for a Musician object that does not exist yet:
    tab_pane.get_by_role("button", name="Band-Mitglied hinzufügen").click()
    ts_control = tab_pane.locator("#id_Band_musiker-1-musiker-ts-control")
    ts_control.click()  # open dropdown
    input_elem = dropdown_input(ts_control)
    with band_popup.expect_request_finished():
        input_elem.fill("John Lennon")
    tab_pane.get_by_text("Keine Ergebnisse")
    tab_pane.get_by_role("link", name=re.compile("hinzufügen", re.IGNORECASE)).click()
    # Save the Band and close the popup.
    band_popup.get_by_role("button", name="Sichern").click()

    page.get_by_role("button", name="Sichern", exact=True).click()
    page.wait_for_url("**/artikel/**")
    page.get_by_text("Testartikel")
    page.get_by_text("The Beatles")
