from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg

from dbentry.base.admin import MIZModelAdmin
from .models import Audio, Band, Musiker, MusikerAudioM2M, Veranstaltung

admin_site = admin.AdminSite(name='test_base')


@admin.register(Audio, site=admin_site)
class AudioAdmin(MIZModelAdmin):
    class MusikerInline(admin.TabularInline):
        model = MusikerAudioM2M

    inlines = [MusikerInline]


@admin.register(Musiker, site=admin_site)
class MusikerAdmin(MIZModelAdmin):
    pass


@admin.register(Band, site=admin_site)
class BandAdmin(MIZModelAdmin):
    list_display = ['band_name', 'alias_string']
    actions = None  # don't include action checkbox in the list_display

    def get_changelist_annotations(self):
        return {
            'alias_list': ArrayAgg(
                'bandalias__alias', distinct=True, ordering='bandalias__alias'
            ),
        }

    def alias_string(self, obj) -> str:
        return ", ".join(obj.alias_list) or self.get_empty_value_display()

    alias_string.short_description = 'Aliase'
    alias_string.admin_order_field = 'alias_list'


@admin.register(Veranstaltung, site=admin_site)
class VeranstaltungAdmin(MIZModelAdmin):
    pass