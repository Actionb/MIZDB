from django.contrib import admin

from tests.test_admin_autocomplete.models import Ausgabe

admin_site = admin.AdminSite(name="test_admin_autocomplete")


@admin.register(Ausgabe, site=admin_site)
class AusgabeAdmin(admin.ModelAdmin):
    pass
