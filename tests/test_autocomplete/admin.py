from django.contrib import admin

from .models import Ausgabe

admin_site = admin.AdminSite(name='test_autocomplete')


@admin.register(Ausgabe, site=admin_site)
class AusgabeAdmin(admin.ModelAdmin):
    pass
