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
def selection_checkbox_locator():
    return "tr input.selection-cb"


@pytest.fixture
def selection_checkboxes(changelist, selection_checkbox_locator):
    """Return all selection checkbox elements."""
    checkboxes = changelist.locator(selection_checkbox_locator)
    for cb in checkboxes.all():
        cb.wait_for(state="attached")
    return checkboxes


@pytest.fixture
def checked_checkboxes():
    """Return all selection checkboxes that are checked."""

    def inner(changelist):
        checkboxes = changelist.locator("tr input.selection-cb:checked")
        for cb in checkboxes.all():
            cb.wait_for(state="attached")
        return checkboxes

    return inner


@pytest.fixture
def select_all_locator():
    return "#select-all-cb"


@pytest.fixture
def select_all_checkbox(changelist, select_all_locator):
    """Return the "select all" checkbox element."""
    elem = changelist.locator(select_all_locator)
    elem.wait_for(state="attached")
    return elem


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
    from playwright.sync_api import Locator

    changelist: Locator
    elem = changelist.get_by_title(re.compile("Ausgewählte Objekte löschen"))
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


@pytest.mark.usefixtures("test_data")
def test_no_view_perms(login_noperms_user, changelist, selection_checkbox_locator, select_all_locator):
    """Assert that no selection checkboxes are shown for users without permission."""
    expect(changelist.locator(selection_checkbox_locator)).to_have_count(0)
    expect(changelist.locator(select_all_locator)).to_have_count(0)


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
    expect(changelist).to_have_title(re.compile("Löschen"))
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Ja")).click()
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

    # Should be on the delete confirmation page now. Confirm the deletion:
    expect(changelist).to_have_title(re.compile("Löschen"))
    with changelist.expect_request_finished():
        changelist.get_by_role("button", name=re.compile("Nein")).click()
    expect(changelist).to_have_title(re.compile("Übersicht"))
    assert _models.Artikel.objects.filter(pk__in=selected_pks).exists()

    # The selected items should still be in the selection:
    expect(selection_panel(changelist)).to_be_visible()
    expect(selected_items(changelist)).to_have_count(2)
