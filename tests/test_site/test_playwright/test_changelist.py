import pytest

from tests.test_site.test_playwright.conftest import CHANGELIST_MODELS, CHANGELIST_VIEW

pytestmark = pytest.mark.e2e


def get_search_term_for_object(obj):
    model = obj._meta.model
    if getattr(model, "name_composing_fields", []):
        field = model.name_composing_fields[0]
        return str(model.objects.filter(pk=obj.pk).values_list(field, flat=True)[0])
    if model._meta.model_name.lower() == "provenienz":
        # Provenienz model has no SearchVectorField itself; it only uses the
        # search field of the related Geber model.
        return str(obj.geber)
    elif model._meta.model_name.lower() == "bestand":
        return str(obj.pk)
    else:
        return str(obj)


@pytest.fixture
def textsearch_input(page):
    search_input = page.get_by_label("Textsuche")
    search_input.wait_for(state="attached")
    return search_input


@pytest.fixture
def search_button(page):
    button = page.get_by_role("button", name="Suchen")
    button.wait_for(state="attached")
    return button


@pytest.fixture
def do_search(page, textsearch_input, search_button, test_object):
    textsearch_input.fill(get_search_term_for_object(test_object))
    with page.expect_request_finished():
        search_button.click()


@pytest.fixture
def results_table(page):
    results = page.locator("table#result_list")
    results.wait_for(state="attached")
    return results


@pytest.mark.parametrize("model", CHANGELIST_MODELS)
@pytest.mark.parametrize("view_name", [CHANGELIST_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_can_search(view_name, model, test_object, do_search, results_table):
    assert results_table.get_by_text(get_search_term_for_object(test_object)).count()
