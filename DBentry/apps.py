from django.apps import AppConfig

class DbentryConfig(AppConfig):
    name = 'DBentry'
    
    def ready(self, *args, **kwargs):
        from DBentry.signals import set_name_changed_flag_ausgabe
        super().ready(*args, **kwargs)
