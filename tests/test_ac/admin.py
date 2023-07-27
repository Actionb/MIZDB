from django.contrib import admin

from .models import Ausgabe

admin_site = admin.AdminSite(name='test_ac')


@admin.register(Ausgabe, site=admin_site)
class AusgabeAdmin(admin.ModelAdmin):
    pass
