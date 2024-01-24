import logging
import re

from django import forms
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.csrf import csrf_failure as django_csrf_failure

logger = logging.getLogger(__name__)

CSRF_FORM_DATA_KEY = "_csrf_form_data"


def _restore_formset(formset, data):
    """
    Modify the formset so that it reflects the changes given by `data`, where
    `data` is the POST data of the request that caused the CSRF failure.

    In effect, this will reset the formset to how it was just before the failed
    POST request, so that the user can confirm the changes.
    """
    select_multiple = (forms.MultipleChoiceField, forms.ModelMultipleChoiceField)
    initial = []
    if formset.instance and formset.forms:
        # A change form with inline formset forms.
        # Collect the initial data for the bound formset forms.
        for i, form in enumerate(formset.forms):
            form_initial = {}
            if not form.instance or not form.instance.pk:
                # This is the one extra empty form. We will append this to
                # formset_initial last, after the new initial data.
                continue
            for field_name, formfield in form.fields.items():
                key = f"{formset.prefix}-{i}-{field_name}"
                if key in data:
                    value = data.pop(key)
                    if not isinstance(formfield, select_multiple) and isinstance(value, list):
                        value = value[0]
                    form_initial[field_name] = value
            initial.append(form_initial)

    # Add the rest of the data as initial_extra.
    initial_extra = []
    pattern = re.compile(f"{formset.prefix}-(?P<index>\d+)-(?P<field>[\w_]+)")  # noqa
    # Group the data items by index:
    indexes = {}
    for k, v in sorted(data.items()):
        m = pattern.search(k)
        if not m:
            continue
        try:
            index = int(m.group("index"))
        except ValueError:  # pragma: no cover
            # The index is not an integer.
            continue
        if index not in indexes:
            indexes[index] = {}
        data = indexes[index]
        data[m.group("field")] = v

    # Walk through the data for each field in each index:
    for index, data in sorted(indexes.items()):
        form_initial = {}
        for field_name, v in data.items():
            if not v or v[0] == "":
                continue
            formfield = formset.forms[0].fields[field_name]
            if not isinstance(formfield, select_multiple):
                v = v[0]
            form_initial[field_name] = v

        if not form_initial:
            # Do not add an empty form now. An empty extra form will later be
            # added to the end of initial_extra.
            continue
        if len(form_initial.keys()) == 1 and formset.fk.name in form_initial:
            # The initial data for this form only contains a value for the
            # InlineForeignKeyField, i.e. it's an 'empty extra' form for a
            # bound formset. Do not include it.
            continue
        else:
            initial_extra.append(form_initial)

    # Append the default empty extra form:
    initial_extra.append({})
    # Update formset attributes:
    formset.initial = initial
    formset.initial_extra = initial_extra
    formset.extra = len(initial_extra)

    # IMPORTANT:
    # The 'forms' property is a cached property. The forms will be constructed
    # only once when the forms property is first accessed - which we have
    # done at the beginning of this function. For the initial data to take
    # effect, the cache must be reset so that the forms will be re-created with
    # the updated data the next time that the property is accessed.
    del formset.forms
    return formset


def csrf_failure(request, reason):
    login_urls = [reverse("login"), reverse("admin:login")]
    logout_urls = [reverse("logout"), reverse("admin:logout")]
    index_urls = [reverse("index"), reverse("admin:index")]
    user_is_logged_in = request.user is not None and request.user.is_authenticated
    warning_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-alert-triangle"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>"""  # noqa
    if request.path in login_urls and user_is_logged_in:
        # A logged-in user has sent a login form with an invalid CSRF token.
        # Assume that the user is trying to log in from a tab with an outdated
        # token that was created before the user had logged in via another tab.
        # Redirect to the login page so that the user may repeat the request,
        # this time with an up-to-date token.
        return HttpResponseRedirect(request.get_full_path())
    elif request.path in logout_urls and not user_is_logged_in:
        # A logout request was sent by an unauthenticated user with an invalid
        # token. Assume that this is a logout request from a user that had
        # logged out already in another tab.
        # Redirect to the respective login page.
        return HttpResponseRedirect(login_urls[logout_urls.index(request.path)])
    elif request.path in logout_urls and user_is_logged_in:
        # A logout request was sent with an invalid token from an authenticated
        # user. Issue a warning message and redirect to the index.
        messages.warning(
            request,
            mark_safe(f"{warning_icon} Abmeldung fehlgeschlagen (CSRF Token ungültig). Sie wurden nicht abgemeldet."),
        )
        return HttpResponseRedirect(index_urls[logout_urls.index(request.path)])
    elif request.path.endswith("add/") or request.path.endswith("change/"):
        # TODO: endswith("add/") too imprecise? Should this check directly
        #  test that the view is included in miz_site.views?
        # User send an add or change form with an invalid token. Store the form
        # data in the session and reload the page. The presence of the data in
        # the session will prompt BaseEditView to restore the form and the
        # formsets.
        messages.warning(
            request,
            mark_safe(
                f"{warning_icon} Speichern fehlgeschlagen (CSRF Token ungültig). "
                "<strong>Datensatz wurde nicht gespeichert.</strong> "
                "Bitte überprüfen Sie die Daten und versuchen Sie es erneut."
            ),
        )
        form_data = request.POST.copy()
        form_data.pop("csrfmiddlewaretoken", None)
        # Convert the QueryDict into a dictionary of lists. The default
        # serializer does not handle QueryDicts properly:
        # https://code.djangoproject.com/ticket/10184
        request.session[CSRF_FORM_DATA_KEY] = dict(form_data.lists())
        return HttpResponseRedirect(request.get_full_path())
    else:
        if user_is_logged_in:
            logger.warning(f"{reason} user: {request.user} ({request.user.pk})")
        return django_csrf_failure(request, reason)


# Log logins and logouts to check if unexpected logouts could be responsible
# for CSRF failures (CSRF token is rotated on login).


@receiver(user_logged_in)
def log_login(sender, user, **kwargs):
    logger.info(f"{user} ({user.pk}) logged in.")


@receiver(user_logged_out)
def log_logout(sender, user=None, **kwargs):
    # user can be None; for example when logging out in one tab and then also
    # logging out in another tab.
    if user is not None:
        logger.info(f"{user} ({user.pk}) logged out.")
