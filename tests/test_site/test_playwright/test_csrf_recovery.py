import pytest
from playwright.sync_api import expect

from dbentry import models as _models
from tests.model_factory import make
from tests.test_site.test_playwright.conftest import CHANGE_VIEW, ADD_VIEW

pytestmark = pytest.mark.e2e


@pytest.fixture
def delete_csrf_token():
    """Set the value of the CSRF token input element to an empty string."""

    def inner(page):
        page.evaluate("""document.querySelector("form.change-form > [name=csrfmiddlewaretoken]").value = "";""")

    return inner


@pytest.fixture
def lennon():
    return make(_models.Musiker, kuenstler_name="John Lennon")


@pytest.fixture
def mccartney():
    return make(_models.Musiker, kuenstler_name="Paul McCartney")


@pytest.fixture
def piano():
    return make(_models.Instrument, instrument="Piano")


@pytest.fixture
def gitarre():
    return make(_models.Instrument, instrument="Gitarre")


@pytest.fixture
def setup_form(page, fill_value, lennon, mccartney, piano, gitarre, delete_csrf_token):
    """Fill the page's form with values."""
    fill_value("titel", "Testaudio")
    fill_value("m2m_audio_musiker_set-0-musiker", lennon.kuenstler_name)
    fill_value("m2m_audio_musiker_set-0-instrument", piano.instrument)
    fill_value("m2m_audio_musiker_set-0-instrument", gitarre.instrument)
    page.get_by_role("button", name="Musiker hinzufügen").click()
    fill_value("m2m_audio_musiker_set-1-musiker", mccartney.kuenstler_name)
    delete_csrf_token(page)


@pytest.fixture
def submit_form(page, save_button):
    """Submit the page's form."""

    def inner():
        with page.expect_response(lambda r: True) as response_info:
            save_button.click()
        return response_info

    return inner


@pytest.fixture
def save_button(page):
    """Return the 'Safe & Continue' button."""
    return page.get_by_role("button", name="Sichern und weiterbearbeiten", exact=True)


@pytest.fixture
def check_form(lennon, mccartney, piano, gitarre):
    """Assert that the change form contains the expected values."""

    def inner(change_form):
        # The form should contain the previous form data:
        expect(change_form.get_by_label("Titel")).to_have_value("Testaudio")
        expect(change_form.locator("#id_m2m_audio_musiker_set-0-musiker")).to_have_value(str(lennon.pk))
        expect(change_form.locator("#id_m2m_audio_musiker_set-1-musiker")).to_have_value(str(mccartney.pk))
        expect(change_form.locator("#id_m2m_audio_musiker_set-0-instrument")).to_have_values(
            [str(gitarre.pk), str(piano.pk)],  # order by instrument name
        )
        # Musiker inline should have four forms:
        # two for the Musiker, one extra form, and one hidden "empty form":
        expect(change_form.locator(".m2m_audio_musiker_set .form-container")).to_have_count(4)

    return inner


@pytest.mark.parametrize("model", [_models.Audio])
@pytest.mark.parametrize("view_name", [ADD_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_csrf_add(
    page,
    view_name,
    model,
    change_form,
    setup_form,
    submit_form,
    get_url,
    check_form,
):
    """Assert that a CSRF failure on add forms gets handled as expected."""
    response_info = submit_form()

    # The user should have been redirected back to the add page:
    url = get_url(f"{model._meta.app_label}_{model._meta.model_name}_{view_name}")
    assert response_info.value.status == 302
    assert page.url == url

    # Assert that the form contains the data of the previous form:
    check_form(change_form)

    # Send the form again. The user should have been redirected to the change
    # page of the created object:
    response_info = submit_form()
    assert response_info.value.status == 302
    assert page.url.endswith("/change/")


@pytest.mark.parametrize("model", [_models.Audio])
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_csrf_change(
    page,
    view_name,
    model,
    change_form,
    setup_form,
    submit_form,
    get_url,
    check_form,
    test_object,
):
    """Assert that a CSRF failure on change forms gets handled as expected."""
    response_info = submit_form()

    # The user should have been redirected back to the change page:
    url = get_url(f"{model._meta.app_label}_{model._meta.model_name}_{view_name}", args=[test_object.pk])
    assert response_info.value.status == 302
    assert page.url == url

    # Assert that the form contains the data of the previous form:
    check_form(change_form)

    # Send the form again. The test object should have been updated:
    submit_form()
    test_object.refresh_from_db()
    assert test_object.titel == "Testaudio"


@pytest.mark.parametrize("model", [_models.Audio])
@pytest.mark.parametrize("view_name", [CHANGE_VIEW])
@pytest.mark.usefixtures("login_superuser")
def test_csrf_empty_extra(
    page,
    view_name,
    model,
    change_form,
    submit_form,
    get_url,
    check_form,
    delete_csrf_token,
    test_object,
):
    """Assert that the formsets do not contain previous 'empty extra' forms."""
    delete_csrf_token(page)
    submit_form()
    musiker_forms = page.locator(".m2m_audio_musiker_set.formset-container > .form-container")
    expect(musiker_forms).to_have_count(1)
