import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.model_factory import make
from tests.test_site.test_playwright.conftest import CHANGELIST_VIEW, ADD_VIEW

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
    return make(model, band_name="Red Hot Chilli Peppers", bandalias__alias="RHCP")


@pytest.mark.django_db
@pytest.mark.parametrize("model", [_models.Band])
@pytest.mark.parametrize("view_name", ["index", CHANGELIST_VIEW, ADD_VIEW])
@pytest.mark.usefixtures("login_superuser")
class TestSearchbar:
    def test_searchbar_search(self, page, searchbar_button, searchbar_modal, searchbar_input):
        """
        User clicks on the searchbar button, types in a search term and sees a
        result.
        """
        expect(searchbar_button).to_be_visible()
        searchbar_button.click()
        expect(searchbar_modal).to_be_visible()
        with page.expect_request_finished():
            searchbar_input.fill("RHCP")
        expect(searchbar_modal.get_by_role("link", name="Red Hot Chilli Peppers")).to_be_attached()
