import re

import pytest

from tests.test_site.test_playwright.conftest import DELETE_VIEW, CRUD_MODELS, CHANGE_VIEW

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("model", CRUD_MODELS)
@pytest.mark.parametrize("view_name", [DELETE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_can_delete(page, view_name, test_object, model, fill_value):
    """Assert that the delete view can be used to delete model objects."""
    pk = test_object.pk
    page.get_by_role("button", name=re.compile("Weiter")).click()
    assert not model.objects.filter(pk=pk).exists(), "Model object was not deleted."


@pytest.mark.parametrize("model", [CRUD_MODELS[0]])
@pytest.mark.parametrize("view_name", [DELETE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_can_abort(page, view_name, test_object, model, fill_value):
    """
    Assert that the object is not deleted if the user clicks the abort button.
    """
    pk = test_object.pk
    page.get_by_role("button", name=re.compile("Abbrechen")).click()
    assert model.objects.filter(pk=pk).exists(), "Model object was deleted unexpectedly."


@pytest.mark.parametrize("model", [CRUD_MODELS[0]])
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])  # start from the change page
@pytest.mark.usefixtures("login_superuser")
def test_abort_redirect_to_previous_page(page, get_url, view_name, test_object, model):
    """
    Assert that the user is sent back to the previous page if they click the
    abort button.
    """
    pk = test_object.pk
    url = get_url(f"{model._meta.app_label}_{model._meta.model_name}_{DELETE_VIEW}", args=[pk])
    page.goto(url)
    page.get_by_role("button", name=re.compile("Abbrechen")).click()
    page.wait_for_url("**/change/")
