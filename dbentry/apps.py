from django.apps import AppConfig


class DbentryConfig(AppConfig):
    name = 'dbentry'

    def ready(self):
        from . import csrf  # noqa
