from django.contrib import admin

from .models import Band, Genre, Kalender, Musiker

admin_site = admin.AdminSite(name='test_tools')


@admin.register(Band, site=admin_site)
class BandAdmin(admin.ModelAdmin):
    pass


@admin.register(Musiker, site=admin_site)
class MusikerAdmin(admin.ModelAdmin):
    pass


@admin.register(Genre, site=admin_site)
class GenreAdmin(admin.ModelAdmin):
    pass


@admin.register(Kalender, site=admin_site)
class KalenderAdmin(admin.ModelAdmin):
    pass
