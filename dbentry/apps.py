from django.apps import AppConfig
from django.contrib.admin.apps import SimpleAdminConfig


class DbentryConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "dbentry"

    def ready(self) -> None:
        from . import csrf  # noqa


class DbentryAdminConfig(SimpleAdminConfig):

    def ready(self) -> None:
        # Import the module with admin models to register them with the site.
        import dbentry.admin.admin  # noqa
