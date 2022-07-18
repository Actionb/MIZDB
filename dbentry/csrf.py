import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.views.csrf import csrf_failure as django_csrf_failure

logger = logging.getLogger(__name__)


def csrf_failure(request, reason):
    logger.warning(f"{reason} user: {request.user} ({request.user.pk})")
    return django_csrf_failure(request, reason)


# Log logins and logouts to check if unexpected logouts could be responsible
# for CSRF failures (CSRF token is rotated on login).


@receiver(user_logged_in)
def log_login(_sender, **kwargs):
    user = kwargs['user']
    logger.info(f'{user} ({user.pk}) logged in.')


@receiver(user_logged_out)
def log_logout(_sender, **kwargs):
    user = kwargs['user']
    logger.info(f'{user} ({user.pk}) logged out.')
