from django.apps import AppConfig


class DbentryConfig(AppConfig):
    name = 'dbentry'

    def ready(self):
        from dbentry.fts import signals  # noqa
