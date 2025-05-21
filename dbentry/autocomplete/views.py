from django.core.exceptions import FieldError
from django.db import transaction
from django.db.models import Q
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


class AutoSuffixAutocompleteView(MIZAutocompleteView):
    """
    A MIZAutocompleteView that automatically adds an appropriate numeric suffix
    to newly created objects that are duplicates of already existing objects.
    """

    def get_query_filter(self, data):
        return Q(**{f"{self.create_field}__regex": rf"^{data[self.create_field]}(\s\(\d+\))*$"})

    def add_suffix(self, data):
        _data = data.copy()  # make the query dict mutable
        count = self.model.objects.filter(self.get_query_filter(data)).count()
        _data[self.create_field] = self.get_suffix(data, count)
        return _data

    def get_suffix(self, data, count):
        if count:
            return f"{data[self.create_field]} ({count + 1})"
        else:
            return data[self.create_field]

    def create_object(self, data):
        return super().create_object(self.add_suffix(data))


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
            if nachname:
                person = _models.Person.objects.create(vorname=vorname, nachname=nachname)
            else:
                person = None
            autor = self.model.objects.create(kuerzel=kuerzel, person=person)
        if person:
            log_addition(self.request.user.pk, person)
        log_addition(self.request.user.pk, autor)
        return autor


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


class AutocompletePerson(AutoSuffixAutocompleteView):
    """Autocomplete view for the Person model that can create new Person objects."""

    def create_object(self, data):
        """
        Create an object given a text.

        Add an addition LogEntry to the django admin log table for the created
        object.
        """
        vorname, nachname = parse_name(data[self.create_field])
        data = self.add_suffix({"vorname": vorname, "nachname": nachname})
        obj = self.model.objects.create(vorname=data["vorname"], nachname=data["nachname"])
        log_addition(self.request.user.pk, obj)
        return obj

    def add_suffix(self, data):
        _data = data.copy()
        count = self.model.objects.filter(self.get_query_filter(data)).count()
        _data["nachname"] = self.get_suffix(data, count)
        return _data

    def get_query_filter(self, data):
        return Q(nachname__regex=rf"^{data['nachname']}(\s\(\d+\))*$") & Q(vorname=data["vorname"])

    def get_suffix(self, data, count):
        if count:
            return f"{data['nachname']} ({count + 1})"
        else:
            return data["nachname"]


class AutocompleteProvenienz(MIZAutocompleteView):
    """
    Autocomplete view for the Provenienz model that returns the str
    representation of an object as values for the label field.
    """

    def get_result_values(self, results):
        return [{self.model._meta.pk.name: r.pk, "text": str(r)} for r in results]


class AutocompleteMostUsed(MIZAutocompleteView):
    """
    An autocomplete view that orders unfiltered results by how often they have
    been used in related Artikel objects.
    """

    def order_queryset(self, queryset):
        ordered = super().order_queryset(queryset)
        if not self.q:
            try:
                return ordered.order_by_most_used("artikel")
            except FieldError:
                # Model has no field "artikel"
                pass
        return ordered


class AutocompleteBand(AutoSuffixAutocompleteView):
    pass


class AutocompleteMusiker(AutoSuffixAutocompleteView):
    pass
