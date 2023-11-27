import os

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from playwright.sync_api import Error

from dbentry.site.registry import miz_site
from dbentry.site.views import *  # import to register views # noqa
from tests.model_factory import make

# https://github.com/microsoft/playwright-python/issues/439
# https://github.com/microsoft/playwright-pytest/issues/29#issuecomment-731515676
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

CHANGELIST_VIEW = "changelist"
ADD_VIEW = "add"
CHANGE_VIEW = "change"
DELETE_VIEW = "delete"
MODEL_VIEW_TYPES = [CHANGELIST_VIEW, ADD_VIEW, CHANGE_VIEW, DELETE_VIEW]

# Models with registered add, change and delete views - except Bestand, which
# only has a view_only mode.
CRUD_MODELS = sorted(
    [m for m in miz_site.views.keys() if m._meta.model_name.lower() != "bestand"],
    key=lambda model: model._meta.model_name
)
# Models with registered changelist views
CHANGELIST_MODELS = sorted(miz_site.changelists.keys(), key=lambda model: model._meta.model_name)


class TrackingHandler:
    """
    A helper object for playwright event handlers that tracks whether the
    handler has been called.

    The actual handler can either be passed in or you can override the handle
    method with the handling logic.

    Use this to verify whether a certain playwright event (f.ex. a dialog event)
    has actually happened.
    """

    def __init__(self, handler=None):
        self.called = False
        self.handler = handler

    def handle(self, *args, **kwargs):
        if self.handler is not None:
            self.handler(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.called = True
        self.handle(*args, **kwargs)

    def __bool__(self):
        return self.called


################################################################################
# Model objects
################################################################################


@pytest.fixture
def model():
    # stub fixture - override with test method parametrization
    return None


@pytest.fixture
def test_object(model):
    """Create a test object for the given model."""
    if model:
        return make(model)
    return None


################################################################################
# Live server
################################################################################


@pytest.fixture
def get_url(live_server):
    """Return the URL for a given view name on the current live server."""

    def inner(view_name, **reverse_kwargs):
        return live_server.url + reverse(view_name, **reverse_kwargs)

    return inner


@pytest.fixture
def page(page, get_url, view_name, model, test_object, context):
    """Navigate to the URL with the given view_name and return the page."""
    # NOTE: context is included as a workaround to a playwright bug:
    #  https://github.com/microsoft/playwright-pytest/issues/172
    reverse_args = None
    if view_name in MODEL_VIEW_TYPES:
        if not model:
            raise ValueError('No model set for a model view. Parametrize "model".')
        if view_name in (CHANGE_VIEW, DELETE_VIEW):
            reverse_args = [test_object.pk]
        view_name = f"{model._meta.app_label}_{model._meta.model_name}_{view_name}"
    url = get_url(view_name, args=reverse_args)
    page.goto(url)
    return page


################################################################################
# Users
################################################################################


@pytest.fixture(autouse=True)
def superuser():
    """Create a superuser."""
    yield get_user_model().objects.create_user(username="admin", password="admin", is_superuser=True)


@pytest.fixture(autouse=True)
def noperms_user():
    """Create a user that has no permissions."""
    yield get_user_model().objects.create_user(username="noperms", password="bar")


################################################################################
# Login
################################################################################


@pytest.fixture
def client_login(client):
    """Log in the given user into the django test client."""

    def inner(user):
        client.force_login(user)
        return client

    return inner


@pytest.fixture
def session_login(client_login, context):
    """
    Log in a user and add the session cookie for the logged-in user to the
    current context.
    """

    def inner(user):
        client = client_login(user)
        auth_cookie = client.cookies["sessionid"]
        pw_cookie = {
            "name": auth_cookie.key,
            "value": auth_cookie.value,
            "path": auth_cookie["path"],
            "domain": auth_cookie["domain"] or "localhost",
        }
        context.add_cookies([pw_cookie])

    return inner


@pytest.fixture
def login_superuser(superuser, session_login):
    """Log in a user with permissions."""
    session_login(superuser)


@pytest.fixture
def login_noperms_user(noperms_user, session_login):
    """Log in a user without permissions."""
    session_login(noperms_user)


################################################################################
# Form handling
################################################################################


@pytest.fixture
def change_form(page):
    """Return the change form of the given page."""
    return page.locator("form.change-form")


@pytest.fixture
def fill_value(page, change_form):
    """Get the form element for the given field_name, and enter the given value."""

    def inner(field_name, value):
        if field_name.lower() == "beschreibung":
            # Open the "Weitere Anmerkungen" accordion first:
            page.get_by_text("Weitere Anmerkungen").click()

        element = change_form.locator(f"[name={field_name}]")
        if element.get_attribute("is-tomselect") is not None:
            # This is the select element that was replaced by a TomSelect
            # element. Tomselect elements need some special handling.
            ts_wrapper = element.locator(":scope ~ div.ts-wrapper")
            ts_wrapper.click()
            dropdown_input = ts_wrapper.locator("input.dropdown-input")
            with page.expect_request_finished():
                dropdown_input.fill(value)
            selectable_options = ts_wrapper.locator("[data-selectable][role=option]")
            selectable_options.first.click()
        else:
            if isinstance(value, bool):
                try:
                    if value:
                        element.check()
                    else:
                        element.uncheck()
                except Error:
                    pass
                else:
                    return
            try:
                element.fill(value)
            except Error:
                # Element could be a boolean select, in which case the boolean
                # value needs to be cast into a string first.
                element.select_option(str(value))

    return inner
