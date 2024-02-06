from django.apps import AppConfig
from django.contrib.admin.apps import SimpleAdminConfig


class DbentryConfig(AppConfig):
    name = "dbentry"

    def ready(self):
        from . import csrf  # noqa


class DbentryAdminConfig(SimpleAdminConfig):

    def ready(self):
        # Import the module with admin models to register them with the site.
        import dbentry.admin.admin  # noqa
