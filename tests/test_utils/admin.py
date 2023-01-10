from django.contrib import admin

from .models import Audio

admin_site = admin.AdminSite(name='test_utils')


@admin.register(Audio, site=admin_site)
class AudioAdmin(admin.ModelAdmin):
    pass
