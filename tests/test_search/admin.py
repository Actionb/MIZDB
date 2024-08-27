from django import forms
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList

from dbentry.search.forms import MIZAdminSearchForm
from dbentry.search.mixins import AdminSearchFormMixin, ChangelistSearchFormMixin, MIZAdminSearchFormMixin

from .models import Artikel, Band

admin_site = admin.AdminSite(name='test_search')


class SearchChangelist(ChangelistSearchFormMixin, ChangeList):
    pass


@admin.register(Band, site=admin_site)
class BandAdmin(AdminSearchFormMixin, admin.ModelAdmin):
    search_form_kwargs = {
        'fields': ['genre', 'years_active'],
        # Specify widget class so that the searchform factory doesn't attempt
        # to create dal autocomplete widgets for these fields:
        'widgets': {
            'genre': forms.widgets.SelectMultiple,
            'musiker': forms.widgets.SelectMultiple
        },
        # The changelist template expects a MIZAdminFormMixin form:
        'form': MIZAdminSearchForm
    }
    fields = ['band_name']


@admin.register(Artikel, site=admin_site)
class ArtikelAdmin(MIZAdminSearchFormMixin, admin.ModelAdmin):
    search_form_kwargs = {
        'fields': [
            'schlagzeile',
            'seite__range',
            'genre',  # m2m
            'ausgabe',  # FK
            'id__in',  # primary key
        ],
        # Specify widget class so that the searchform factory doesn't attempt
        # to create dal autocomplete widgets for these fields:
        'widgets': {
            'genre': forms.widgets.SelectMultiple,
            'ausgabe': forms.widgets.Select
        },
        # The changelist template expects a MIZAdminFormMixin form:
        'form': MIZAdminSearchForm
    }

    def get_changelist(self, request, **kwargs):
        return SearchChangelist
