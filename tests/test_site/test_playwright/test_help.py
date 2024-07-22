import re

import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from dbentry.site.registry import miz_site
from tests.test_site.test_playwright.conftest import CHANGE_VIEW, CHANGELIST_VIEW

pytestmark = pytest.mark.e2e

# Models without dedicated help pages:
excluded = [
    "audiomedium",
    "bestand",
    "bildreihe",
    "geber",
    "plattenfirma",
    "schriftenreihe",
    "veranstaltungsreihe",
    "videomedium",
]
MODELS_WITH_HELP_PAGES = sorted(
    [m for m in miz_site.views.keys() if m._meta.model_name.lower() not in excluded],
    key=lambda model: model._meta.model_name,
)


@pytest.fixture
def help_link(page):
    return page.get_by_role("link", name="Hilfe")


def get_expected_title(model):
    defaults = {
        _models.Brochure: "Broschüre",
        _models.Kalender: "Programmheft",
    }
    return defaults.get(model, model._meta.model_name)


@pytest.mark.parametrize("model", MODELS_WITH_HELP_PAGES)
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_has_help_page_edit(page, model, view_name, help_link):
    """
    Assert that clicking on the 'help' button on an edit page sends the user to
    the corresponding help page.
    """
    with page.expect_event("popup") as page_info:
        help_link.click()
    popup = page_info.value
    expect(popup).to_have_title(re.compile(get_expected_title(model), re.IGNORECASE))


@pytest.mark.parametrize("model", MODELS_WITH_HELP_PAGES)
@pytest.mark.parametrize("view_name", [CHANGELIST_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_has_help_page_changelist(page, model, view_name, help_link):
    """
    Assert that clicking on the 'help' button on a changelist sends the user to
    the corresponding help page.
    """
    help_link.click()
    expect(page).to_have_title(re.compile(get_expected_title(model), re.IGNORECASE))
