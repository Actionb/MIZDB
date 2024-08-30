import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.model_factory import make

pytestmark = pytest.mark.e2e


@pytest.fixture
def view_name():
    return "dbentry_artikel_changelist"


@pytest.fixture
def changelist(page):
    return page


@pytest.fixture
def changelist_results():
    """Return the table rows of the changelist results."""

    def inner(changelist):
        # select all rows, except those in the table header:
        return changelist.get_by_role("row").filter(has_not=changelist.get_by_role("columnheader"))

    return inner


@pytest.fixture
def artikel_data():
    magazin = make(_models.Magazin, magazin_name="Testmagazin")
    ausgabe = make(_models.Ausgabe, magazin=magazin, ausgabejahr__jahr="2023", ausgabemonat__monat__monat="Oktober")
    return [make(_models.Artikel, ausgabe=ausgabe) for _ in range(101)]


@pytest.fixture
def band_data():
    return [make(_models.Band) for _ in range(50)]


@pytest.fixture
def test_data(artikel_data, band_data):
    return artikel_data, band_data


@pytest.fixture
def get_selection_checkboxes(changelist_results):
    """Return the selection checkbox element for the given changelist."""

    def inner(changelist):
        return changelist_results(changelist).get_by_role("checkbox")

    return inner


@pytest.fixture
def selection_checkboxes(changelist, get_selection_checkboxes):
    """Return all selection checkbox elements."""
    return get_selection_checkboxes(changelist)


@pytest.fixture
def checked_checkboxes(get_selection_checkboxes):
    """Return all selection checkboxes that are checked."""

    def inner(changelist):
        checkboxes = get_selection_checkboxes(changelist).locator(":scope:checked")
        for cb in checkboxes.all():
            cb.wait_for(state="attached")
        return checkboxes

    return inner


@pytest.fixture
def select_all_checkbox(changelist):
    """Return the "select all" checkbox element."""
    return changelist.get_by_label("Alle auswählen")


@pytest.fixture
def selection_panel():
    """Return the panel that shows the currently selected items."""

    def inner(changelist):
        elem = changelist.locator("#selection-panel")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def panel_header(selection_panel):
    """Return the selection panel header."""

    def inner(changelist):
        elem = selection_panel(changelist).locator(".accordion-header")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def selected_items_container(selection_panel):
    """Return the panel container that lists the selected items."""

    def inner(changelist):
        elem = selection_panel(changelist).locator("#selected-items-container")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def selected_items(selected_items_container):
    """Return the selected items as shown in the selection panel."""

    def inner(changelist):
        items = selected_items_container(changelist).locator(".selected-item")
        for item in items.all():
            item.wait_for(state="attached")
        return items

    return inner


@pytest.fixture
def remove_button():
    """Return the remove button for the given selected item."""

    def inner(selected_item):
        elem = selected_item.locator(".remove-selection")
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.fixture
def clear_all(changelist):
    """Return the "clear all" button."""
    elem = changelist.locator("#clear-selection")
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def selected_pk():
    """Return the primary key value of the selected object."""

    def inner(selection_checkbox):
        return selection_checkbox.get_attribute("value")

    return inner


@pytest.fixture
def selected_object(selected_pk):
    """Return the model instance of the selected object."""

    def inner(selection_checkbox):
        return _models.Artikel.objects.get(pk=selected_pk(selection_checkbox))

    return inner


@pytest.fixture
def delete_action_button(changelist):
    """Return the button for the 'delete' action."""
    elem = changelist.get_by_title(re.compile("Ausgewählte Objekte löschen"))
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def merge_action_button(changelist):
    """Return the button for the 'merge' action."""
    elem = changelist.get_by_title(re.compile("ausgewählten Objekte in einziges Objekt zusammenfügen"))
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def action_selection_button(changelist):
    """Return the button that opens the action selection dropdown."""
    elem = changelist.get_by_text(re.compile("Aktion"))
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def action_selection_dropdown(action_selection_button):
    """Return the dropdown for the action selection."""
    elem = action_selection_button.locator(":scope ~ .dropdown-menu")
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def get_action_button(action_selection_button, action_selection_dropdown):
    """Return the action submit button for the given action name."""

    def inner(action_name):
        action_selection_button.click()
        elem = action_selection_dropdown.get_by_text(action_name)
        elem.wait_for(state="attached")
        return elem

    return inner


@pytest.mark.usefixtures("test_data", "login_superuser")
def test_selection(
    get_url,
    changelist,
    view_name,
    selection_checkboxes,
    panel_header,
    selected_items,
    selected_object,
    selected_pk,
    remove_button,
    checked_checkboxes,
    select_all_checkbox,
    clear_all,
):
    """Test selecting rows and using the selection container/panel."""
    # Select the first row.
    cb = selection_checkboxes.first
    cb.click()
    header = panel_header(changelist)
    expect(header).to_have_text("Ausgewählte Artikel (1)")
    header.click()
    selected = selected_items(changelist)
    expect(selected).to_be_visible()
    expect(selected).to_have_count(1)
    expect(selected.first).to_have_text(selected_object(cb).schlagzeile)

    # Select a second row.
    cb = selection_checkboxes.nth(10)
    cb.click()
    header = panel_header(changelist)
    expect(header).to_have_text("Ausgewählte Artikel (2)")
    selected = selected_items(changelist)
    expect(selected).to_have_count(2)
    expect(selected.nth(1)).to_have_text(selected_object(cb).schlagzeile)

    # Click the remove button for the second selected item.
    remove_button(selected.nth(1)).click()
    header = panel_header(changelist)
    expect(header).to_have_text("Ausgewählte Artikel (1)")
    selected = selected_items(changelist)
    expect(selected).to_have_count(1)
    expect(selected).not_to_have_text(selected_object(cb).schlagzeile)
    expect(cb).not_to_be_checked()

    # Close the selection panel.
    header.click()
    expect(selected).not_to_be_visible()

    # Check the "select all" checkbox.
    select_all_checkbox.click()
    header = panel_header(changelist)
    header.click()
    expect(header).to_have_text("Ausgewählte Artikel (100)")
    selected = selected_items(changelist)
    expect(selected).to_have_count(100)

    # Go to another changelist, and select items there:
    changelist.goto(get_url("dbentry_band_changelist"))
    changelist.wait_for_url("**")
    # No changelist header should be shown, since we haven't selected anything
    # yet:
    header = panel_header(changelist)
    expect(header).not_to_be_visible()
    # Select a row:
    cb = selection_checkboxes.first
    cb.click()
    expect(header).to_have_text("Ausgewählte Bands (1)")
    header.click()
    selected = selected_items(changelist)
    expect(selected).to_be_visible()
    expect(selected).to_have_count(1)
    band = _models.Band.objects.get(pk=selected_pk(cb))
    expect(selected.first).to_have_text(band.band_name)

    # Return to the Artikel changelist. Item selection should be loaded from
    # local storage.
    changelist.goto(get_url(view_name))
    header = panel_header(changelist)
    header.click()
    expect(header).to_have_text("Ausgewählte Artikel (100)")
    selected = selected_items(changelist)
    expect(selected).to_have_count(100)

    # Use the "clear all" button.
    clear_all.click()
    header = panel_header(changelist)
    expect(header).not_to_be_visible()
    selected = selected_items(changelist)
    expect(selected).to_have_count(0)
    expect(checked_checkboxes(changelist)).to_have_count(0)


@pytest.mark.usefixtures("test_data", "login_superuser")
def test_delete_action(
    changelist,
    selection_checkboxes,
    selected_pk,
    selection_panel,
    delete_action_button,
    selected_items,
):
    """
    Assert that the deletion confirmation page is shown for the selected items
    and that they will be deleted if confirmed.
    """
    # Select the first two items:
    cb1 = selection_checkboxes.first
    cb1.check()
    cb2 = selection_checkboxes.nth(1)
    cb2.check()
    selected_pks = [selected_pk(cb1), selected_pk(cb2)]

    # Select the delete action:
    selection_panel(changelist).click()
    delete_action_button.click()

    # Should be on the delete confirmation page now. Confirm the deletion:
    expect(changelist).to_have_title(re.compile("Sind Sie sicher"))
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Weiter")).click()
    expect(changelist).to_have_title(re.compile("Übersicht"))
    assert not _models.Artikel.objects.filter(pk__in=selected_pks).exists()

    # The deleted items should not be in the selection:
    expect(selection_panel(changelist)).not_to_be_visible()
    expect(selected_items(changelist)).to_have_count(0)


@pytest.mark.usefixtures("test_data", "login_superuser")
def test_delete_action_abort(
    changelist,
    selection_checkboxes,
    selected_pk,
    selection_panel,
    delete_action_button,
    selected_items,
):
    """
    Assert that clicking the abort button on the confirmation page does not
    delete the selected items.
    """
    # Select the first two items:
    cb1 = selection_checkboxes.first
    cb1.check()
    cb2 = selection_checkboxes.nth(1)
    cb2.check()
    selected_pks = [selected_pk(cb1), selected_pk(cb2)]

    # Select the delete action:
    selection_panel(changelist).click()
    delete_action_button.click()

    # Should be on the delete confirmation page now. Abort:
    expect(changelist).to_have_title(re.compile("Sind Sie sicher"))
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Abbrechen")).click()
    expect(changelist).to_have_title(re.compile("Übersicht"))
    assert _models.Artikel.objects.filter(pk__in=selected_pks).exists()

    # The selected items should still be in the selection:
    expect(selection_panel(changelist)).to_be_visible()
    expect(selected_items(changelist)).to_have_count(2)


@pytest.fixture
def merge_data():
    """Test data for the merge action tests."""
    magazin = make(_models.Magazin)
    ausgabe = make(_models.Ausgabe, magazin=magazin)
    primary = make(_models.Artikel, schlagzeile="Primary", ausgabe=ausgabe)
    secondary1 = make(_models.Artikel, schlagzeile="Secondary1", beschreibung="foo", ausgabe=ausgabe)
    secondary2 = make(_models.Artikel, schlagzeile="Secondary2", beschreibung="bar", ausgabe=ausgabe)
    return primary, secondary1, secondary2


@pytest.mark.usefixtures("login_superuser")
def test_merge_action(
    merge_data,
    changelist,
    select_all_checkbox,
    selection_panel,
    merge_action_button,
    selection_checkboxes,
    selected_items,
    changelist_results,
):
    """User merges three objects."""
    primary, secondary1, _secondary2 = merge_data
    select_all_checkbox.click()
    selection_panel(changelist).click()
    merge_action_button.click()

    # Should be on page for step 1 now:
    expect(changelist).to_have_title(re.compile("Merge.*step 1"))

    # Select the primary and proceed:
    changelist.get_by_role("row", name=re.compile(primary.schlagzeile)).get_by_role("checkbox").check()
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Weiter")).click()

    # Should be on the step 2 (conflict resolution) now:
    expect(changelist).to_have_title(re.compile("Merge.*step 2"))

    # Select a value to use for the 'beschreibung' field, and proceed:
    changelist.get_by_label(secondary1.beschreibung).check()
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Weiter")).click()

    # Should be back on the changelist, with the updated primary as the only
    # result:
    expect(changelist).to_have_title(re.compile("Übersicht"))
    results = changelist_results(changelist)
    expect(results).to_have_count(1)
    expect(results.first.get_by_role("link")).to_have_text(re.compile(primary.schlagzeile))

    # Check that the secondary instances have been removed from the selection
    # panel:
    expect(selection_panel(changelist)).to_be_visible()
    selection_panel(changelist).click()
    items = selected_items(changelist)
    expect(items).to_have_count(1)
    expect(items.get_by_role("link", name=re.compile(primary.schlagzeile))).to_be_visible()

    # Check the model instance:
    assert _models.Artikel.objects.filter(pk=primary.pk).exists()
    primary.refresh_from_db()
    assert primary.schlagzeile == "Primary"
    assert primary.beschreibung == "foo"


@pytest.mark.usefixtures("login_superuser")
def test_merge_action_no_expand(
    merge_data,
    changelist,
    select_all_checkbox,
    selection_panel,
    merge_action_button,
    selection_checkboxes,
    selected_items,
    changelist_results,
):
    """User merges three objects, without 'expanding the primary'."""
    primary, *_ = merge_data
    select_all_checkbox.click()
    selection_panel(changelist).click()
    merge_action_button.click()

    # Should be on page for step 1 now:
    expect(changelist).to_have_title(re.compile("Merge.*step 1"))
    changelist.get_by_label(re.compile("erweitern")).uncheck()

    # Select the primary and proceed:
    changelist.get_by_role("row", name=re.compile(primary.schlagzeile)).get_by_role("checkbox").check()
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Weiter")).click()

    # Should be back on the changelist (there cannot be conflicts with
    # expand_primary=False), with the updated primary as the only result:
    expect(changelist).to_have_title(re.compile("Übersicht"))
    results = changelist_results(changelist)
    expect(results).to_have_count(1)
    expect(results.first.get_by_role("link")).to_have_text(re.compile(primary.schlagzeile))

    # Check that the secondary instances have been removed from the selection
    # panel:
    expect(selection_panel(changelist)).to_be_visible()
    selection_panel(changelist).click()
    items = selected_items(changelist)
    expect(items).to_have_count(1)
    expect(items.get_by_role("link", name=re.compile(primary.schlagzeile))).to_be_visible()


@pytest.fixture
def export_action_button(changelist):
    return changelist.get_by_title("Die ausgewählten Objekte exportieren")


@pytest.mark.usefixtures("artikel_data", "login_superuser")
def test_export_action(
    get_url,
    changelist,
    view_name,
    selection_checkboxes,
    panel_header,
    export_action_button,
):
    """User exports an Artikel object via the changelist export action."""
    selection_checkboxes.first.click()
    panel_header(changelist).click()
    expect(export_action_button).to_be_visible()
    export_action_button.click()
    changelist.wait_for_url("**")
    expect(changelist).to_have_title(re.compile("Export", re.IGNORECASE))
    changelist.get_by_label("Dateiformat").select_option("csv")
    with changelist.expect_download():
        changelist.get_by_role("button", name="Exportieren").click()
