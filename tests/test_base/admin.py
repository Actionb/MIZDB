from django.contrib import admin

from dbentry.base.admin import MIZModelAdmin
from .models import Audio, Band, Musiker, MusikerAudioM2M, Veranstaltung, Person

admin_site = admin.AdminSite(name='test_base')


@admin.register(Audio, site=admin_site)
class AudioAdmin(MIZModelAdmin):
    class MusikerInline(admin.TabularInline):
        model = MusikerAudioM2M

    inlines = [MusikerInline]
    fields = ["titel", "tracks", "beschreibung"]


@admin.register(Musiker, site=admin_site)
class MusikerAdmin(MIZModelAdmin):
    pass


@admin.register(Band, site=admin_site)
class BandAdmin(MIZModelAdmin):
    list_display = ['band_name', 'alias_string']
    actions = None  # don't include action checkbox in the list_display

    def alias_string(self, obj) -> str:
        return ", ".join(obj.alias_list) or self.get_empty_value_display()

    alias_string.short_description = 'Aliase'
    alias_string.admin_order_field = 'alias_list'


@admin.register(Veranstaltung, site=admin_site)
class VeranstaltungAdmin(MIZModelAdmin):
    pass


@admin.register(Person, site=admin_site)
class PersonAdmin(MIZModelAdmin):
    require_confirmation = True
