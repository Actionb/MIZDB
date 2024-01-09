import logging

from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth.views import redirect_to_login
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.csrf import csrf_failure as django_csrf_failure

logger = logging.getLogger(__name__)


def csrf_failure(request, reason):
    login_urls = [reverse("login"), reverse("admin:login")]
    logout_urls = [reverse("logout"), reverse("admin:logout")]
    index_urls = [reverse("index"), reverse("admin:index")]
    user_is_logged_in = request.user is not None and request.user.is_authenticated
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
            "Abmeldung fehlgeschlagen (CSRF Token ungültig). Sie wurden nicht abgemeldet.",
        )
        return HttpResponseRedirect(index_urls[logout_urls.index(request.path)])
    if user_is_logged_in:
        logger.warning(f"{reason} user: {request.user} ({request.user.pk})")
    return django_csrf_failure(request, reason)


# Log logins and logouts to check if unexpected logouts could be responsible
# for CSRF failures (CSRF token is rotated on login).


@receiver(user_logged_in)
def log_login(sender, user, **kwargs):
    logger.info(f'{user} ({user.pk}) logged in.')


@receiver(user_logged_out)
def log_logout(sender, user=None, **kwargs):
    # user can be None; for example when logging out in one tab and then also
    # logging out in another tab.
    if user is not None:
        logger.info(f'{user} ({user.pk}) logged out.')
