import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.model_factory import make
from tests.test_site.test_playwright.conftest import ADD_VIEW, CHANGELIST_VIEW

pytestmark = pytest.mark.e2e


@pytest.fixture
def searchbar_button(page):
    elem = page.get_by_role("button", name="Datenbanksuche")
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def searchbar_modal(page):
    elem = page.locator("#searchModal")
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def searchbar_input(searchbar_modal):
    elem = searchbar_modal.get_by_placeholder(re.compile("Suchbegriff"))
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def test_object(model):
    return make(model, band_name="Red Hot & Chilli Peppers", bandalias__alias="RHCP")


@pytest.mark.django_db
@pytest.mark.parametrize("model", [_models.Band])
@pytest.mark.parametrize("view_name", ["index", CHANGELIST_VIEW, ADD_VIEW])
@pytest.mark.usefixtures("login_superuser")
class TestSearchbar:
    @pytest.fixture
    def search(self, page, searchbar_button, searchbar_modal, searchbar_input):
        def inner(search_term):
            expect(searchbar_button).to_be_visible()
            searchbar_button.click()
            expect(searchbar_modal).to_be_visible()
            with page.expect_request_finished():
                searchbar_input.fill(search_term)
            return searchbar_modal

        return inner

    def test_searchbar_search(self, search):
        """
        User clicks on the searchbar button, types in a search term and sees a
        result.
        """
        results = search("Hot & Chilli")
        expect(results.get_by_role("link", name="BAND")).to_be_attached()
        expect(results.get_by_role("link", name="Red Hot & Chilli Peppers")).to_be_attached()

    def test_click_on_category_opens_changelist(self, page, view_name, search):
        """
        When the user clicks on the link of one of the search results, it should
        send the user to the particular changelist, with the search term
        inserted into the textsearch input.
        """
        results = search("Hot & Chilli")
        result_link = results.get_by_role("link", name="BAND")
        if view_name == "add":
            # The result links open the relevant page in a new tab if the user
            # is on the 'add' view.
            with page.expect_popup() as popup_info:
                result_link.click()
            page = popup_info.value
        else:
            result_link.click()
        expect(page).to_have_title(re.compile("^Bands Übersicht.*"))
        search_box = page.get_by_label("Textsuche")
        expect(search_box).to_have_value("Hot & Chilli")
