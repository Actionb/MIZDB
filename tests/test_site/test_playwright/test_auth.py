import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("view_name", ["login"])
def test_login(page, view_name, superuser):
    """Fill out the login form and log in."""
    page.get_by_label("Benutzername").fill("admin")
    page.get_by_label("Passwort").fill("admin")
    with page.expect_response(page.url) as response_info:
        page.get_by_role("button", name="Anmelden").click()
    response = response_info.value
    assert response.status == 302


@pytest.mark.parametrize("view_name", ["password_change"])
def test_password_change(login_superuser, page, view_name, superuser):
    """Change the user password."""
    old_password = "admin"
    new_password = "foobar12"
    page.get_by_label("Altes Passwort").fill(old_password)
    page.get_by_label("Neues Passwort").all()[0].fill(new_password)
    page.get_by_label("Neues Passwort bestätigen").fill(new_password)
    page.get_by_role("button", name="OK").click()
    superuser.refresh_from_db()
    assert superuser.check_password(new_password)
