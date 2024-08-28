import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.test_site.test_playwright.conftest import CHANGE_VIEW, TrackingHandler

pytestmark = pytest.mark.e2e

DIRTY_CLASS = "_dirty"


class DialogHandler(TrackingHandler):
    def __init__(self, accept=True):
        super().__init__()
        self.accept = accept

    def handle(self, dialog):
        if self.accept:
            dialog.accept()
        else:
            dialog.dismiss()


@pytest.fixture
def dirty_elem(page):
    elem = page.get_by_label("Bandname")
    elem.wait_for(state="attached")
    return elem


@pytest.fixture
def make_dirty(page, dirty_elem):
    dirty_elem.fill("Foo")
    page.keyboard.press("Tab")  # make elem lose focus to trigger change event


@pytest.fixture
def dialog_handler(page):
    handler = DialogHandler()
    page.on("dialog", handler)
    return handler


@pytest.mark.parametrize("model", [_models.Band])
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])
@pytest.mark.usefixtures("login_superuser", "test_object")
class TestDirty:
    def test_adds_dirty_class(self, page, dirty_elem, make_dirty):
        """Assert that the expected 'dirty' CSS class is added to the dirty element."""
        expect(dirty_elem).to_have_class(re.compile(DIRTY_CLASS))

    def test_issues_alert(self, page, make_dirty, dialog_handler):
        """
        Assert that an alert is issued if the user tries to leave the page with
        unsaved changes.
        """
        page.get_by_role("link", name="MIZDB").click()
        # Note that page.close(run_before_unload=True) does not seem to work
        #  here.
        assert dialog_handler.called

    def test_no_alert_when_submitting(self, page, make_dirty, dialog_handler):
        """Assert that no alert is issued if the user submits a dirty form."""
        page.get_by_role("button", name="Sichern", exact=True).click()
        assert not dialog_handler.called

    def test_form_reset_removes_dirty_class(self, page, dirty_elem, make_dirty):
        """
        Assert that resetting the form removes the 'dirty' CSS class from the
        dirty element.
        """
        page.locator("form.change-form").evaluate("form => form.reset()")
        expect(dirty_elem).not_to_have_class(re.compile(DIRTY_CLASS))

    def test_flags_only_change_form_elements(self, page):
        """
        Assert that only form elements of the change form are flagged with the
        dirty class.
        """
        page.get_by_text("Datenbanksuche").click()
        search_input = page.get_by_placeholder("Suchbegriff eingeben...")
        search_input.fill("foo")
        expect(search_input).not_to_have_class(re.compile(DIRTY_CLASS))
