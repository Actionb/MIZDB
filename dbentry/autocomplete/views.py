from django.db import transaction
from mizdb_tomselect.views import AutocompleteView
from nameparser import HumanName
from stdnum import issn

from dbentry import models as _models
from dbentry.utils.admin import log_addition
from dbentry.utils.text import parse_name


class MIZAutocompleteView(AutocompleteView):
    """Base view class for autocomplete requests."""

    def get_page_results(self, page):
        return page.object_list.overview(*self.values_select)

    def search(self, queryset, q):
        if q:
            return queryset.search(q)
        return queryset

    def order_queryset(self, queryset):
        if self.q:
            # search may have already applied ordering - do not override
            return queryset
        return super().order_queryset(queryset)

    def create_object(self, data):
        obj = super().create_object(data)
        log_addition(self.request.user.pk, obj)
        return obj


class AutocompleteAusgabe(MIZAutocompleteView):
    """Autocomplete view for the Ausgabe model that applies chronological ordering."""

    def order_queryset(self, queryset):
        if self.q:
            # search may have already applied ordering - do not override
            return queryset
        return queryset.chronological_order()


class AutocompleteAutor(MIZAutocompleteView):
    """Autocomplete view for the Autor model that can create new Autor objects."""

    def create_object(self, data):
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        hn = HumanName(data[self.create_field])
        # The nickname will be used as the 'kuerzel' for the Autor instance.
        # Shorten the nickname to respect the max_length of the 'kuerzel' field:
        vorname, nachname, kuerzel = " ".join([hn.first, hn.middle]).strip(), hn.last, hn.nickname[:8]
        with transaction.atomic():
            person = _models.Person.objects.create(vorname=vorname, nachname=nachname)
            obj = self.model.objects.create(kuerzel=kuerzel, person=person)
        log_addition(self.request.user.pk, person)
        log_addition(self.request.user.pk, obj)
        return obj


class AutocompleteBuchband(MIZAutocompleteView):
    """Autocomplete view that queries Buch instances that are defined as buchband."""

    queryset = _models.Buch.objects.filter(is_buchband=True)


class AutocompleteMagazin(MIZAutocompleteView):
    """Autocomplete view for the Magazin model that can handle ISSN search terms."""

    def search(self, queryset, q):
        # Compact-ify the search term if it is a valid ISSN.
        if issn.is_valid(q):
            q = issn.compact(q)
        return super().search(queryset, q)


class AutocompletePerson(MIZAutocompleteView):
    """Autocomplete view for the Person model that can create new Person objects."""

    def create_object(self, data):
        """
        Create an object given a text.

        Add an addition LogEntry to the django admin log table for the created
        object.
        """
        vorname, nachname = parse_name(data[self.create_field])
        obj = self.model.objects.create(vorname=vorname, nachname=nachname)
        log_addition(self.request.user.pk, obj)
        return obj
