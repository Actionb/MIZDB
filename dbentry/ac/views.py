from typing import Any, List, Optional, Tuple, Type

# noinspection PyPackageRequirements
from dal import autocomplete
from django import http
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Page, Paginator
from django.db import transaction
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.utils.functional import cached_property
from django.utils.translation import gettext
from nameparser import HumanName
from stdnum import issn

from dbentry import models as _models
from dbentry.ac.widgets import EXTRA_DATA_KEY
from dbentry.query import AusgabeQuerySet, MIZQuerySet
from dbentry.sites import miz_site
from dbentry.utils.admin import log_addition
from dbentry.utils.gnd import searchgnd
from dbentry.utils.models import get_model_from_string
from dbentry.utils.text import parse_name


def parse_autor_name(name: str) -> tuple[str, str, str]:
    """Split up ``name`` into first name(s), last name and nickname."""
    hn = HumanName(name)
    # The nickname will be used as the 'kuerzel' for the Autor instance.
    # Shorten the nickname to respect the max_length of the 'kuerzel' field:
    return " ".join([hn.first, hn.middle]).strip(), hn.last, hn.nickname[:8]


class ACBase(autocomplete.Select2QuerySetView):
    """Base view for the autocomplete views of the dbentry app."""

    model: Type[Model]
    create_field: Optional[str]

    # Do not show the create option, if the results contain an exact match.
    prevent_duplicates: bool = False

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """Set model and create_field instance attributes."""
        super().setup(request, *args, **kwargs)
        if not self.model:
            self.model = get_model_from_string(kwargs.pop('model_name'))
        if self.create_field is None:
            self.create_field = kwargs.pop('create_field', None)

    def display_create_option(self, context: dict, q: str) -> bool:
        """Return a boolean whether the create option should be displayed."""
        if self.create_field and q:
            if self.prevent_duplicates:
                # Don't offer to create a new option, if a case-insensitive
                # identical one already exists.
                existing_options = (
                    self.get_result_label(result).lower()
                    for result in context['object_list']
                )
                if q.lower() in existing_options:
                    return False
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                return True
        return False

    def build_create_option(self, q: str) -> list:
        """Construct the create option item to be appended to the results."""
        return [{
            'id': q,
            'text': gettext('Create "%(new_value)s"') % {'new_value': q},
            'create_id': True,
        }]

    def get_create_option(self, context: dict, q: str) -> list:
        """Return the create option item to be appended to the results."""
        # Note that q can be None (see: Select2ViewMixin.render_to_response).
        if q is None:
            q = ''
        else:
            q = q.strip()

        if self.has_add_permission(self.request) and self.display_create_option(context, q):
            return self.build_create_option(q)
        return []

    def get_ordering(self) -> list:
        """Return the field or fields to use for ordering the queryset."""
        # noinspection PyUnresolvedReferences
        return super().get_ordering() or self.model._meta.ordering

    def get_search_results(self, queryset: QuerySet, search_term: str) -> QuerySet:
        """Filter the results based on the query."""
        queryset = self.apply_forwarded(queryset)
        search_term = search_term.strip()
        if search_term and isinstance(queryset, MIZQuerySet):
            return queryset.search(search_term)
        return super().get_search_results(queryset, search_term)

    def apply_forwarded(self, queryset: QuerySet) -> QuerySet:
        """Apply filters based on the forwarded values to the given queryset."""
        if not self.forwarded:
            return queryset
        forward_filter = {}
        for k, v in self.forwarded.items():
            # Remove 'empty' forward items.
            if k and v:
                forward_filter[k] = v
        if not forward_filter:
            # All forwarded items were empty; return an empty queryset.
            # noinspection PyUnresolvedReferences
            return self.model.objects.none()
        return queryset.filter(**forward_filter)

    def create_object(self, text: str) -> Model:
        """
        Create an object given a text.

        Add an addition LogEntry to the django admin log table for the created
        object.
        """
        # Don't use get_or_create here as we need to allow creating 'duplicates'
        # of already existing instances on some models: f.ex. two bands with
        # the same name.
        # noinspection PyUnresolvedReferences
        obj = self.model.objects.create(**{self.create_field: text.strip()})
        log_addition(self.request.user.pk, obj)
        return obj


class ACTabular(ACBase):
    """
    Autocomplete view that presents the result data in tabular form.

    Select2 will group the results returned by the JsonResponse into option
    groups (optgroup). This (plus bootstrap grids) will allow useful
    presentation of the data.

    Attributes:
        - overview_annotations (tuple): a sequence of field paths/annotations to
          use as arguments to queryset.overview().
    """

    overview_annotations: tuple = ()

    def get_queryset(self) -> QuerySet:
        # Apply overview annotations and optimizations:
        return super().get_queryset().overview(*self.overview_annotations)

    def get_extra_data(self, result: Model) -> list:
        """Return the additional data to be displayed for the given result."""
        return []  # pragma: no cover

    def get_group_headers(self) -> list:
        """Return a list of labels for the additional columns/group headers."""
        return []  # pragma: no cover

    def get_results(self, context: dict) -> List[dict]:
        """Return data for the 'results' key of the response."""
        return [
            {
                'id': self.get_result_value(result),
                'text': self.get_result_label(result),
                EXTRA_DATA_KEY: self.get_extra_data(result),
                'selected_text': self.get_selected_result_label(result),
            }
            for result in context['object_list']
        ]

    def render_to_response(self, context: dict) -> http.JsonResponse:
        """
        Return a JSON response in Select2 format.

        If there are search results to display, nest the list of result items
        under 'children' of the 'results' item so that Select2 creates an
        optgroup for the results. See:
        https://select2.org/data-sources/formats#grouped-data
        """
        q = self.request.GET.get('q', None)

        create_option = self.get_create_option(context, q)
        result_list = self.get_results(context)
        if self.request.GET.get('tabular') and result_list:
            headers = []
            if context['page_obj'] and not context['page_obj'].has_previous():
                # Only add optgroup headers for the first page of results.
                headers = self.get_group_headers()

            # noinspection PyUnresolvedReferences
            results = [{
                "text": self.model._meta.verbose_name,
                "children": result_list + create_option,
                "is_optgroup": True,
                "optgroup_headers": headers,
            }]
        else:
            results = result_list + create_option

        return http.JsonResponse(
            {'results': results, 'pagination': {'more': self.has_more(context)}}
        )


###############################################################################
# Concrete autocomplete views.
###############################################################################


class ACAusgabe(ACTabular):
    """
    Autocomplete view for the model ausgabe that applies chronological order to
    the results.
    """

    model = _models.Ausgabe
    overview_annotations = ('num_list', 'lnum_list', 'jahr_list')

    def get_queryset(self) -> AusgabeQuerySet:
        return super().get_queryset().chronological_order()

    def get_group_headers(self) -> list:
        return ['Nummer', 'lfd.Nummer', 'Jahr']

    def get_extra_data(self, result: _models.Ausgabe) -> list:
        # noinspection PyUnresolvedReferences
        return [result.num_list, result.lnum_list, result.jahr_list]


class ACAutor(ACBase):
    model = _models.Autor
    create_field = '__any__'

    def create_object(self, text: str) -> _models.Autor:
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        vorname, nachname, kuerzel = parse_autor_name(text)
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

    def build_create_option(self, q: str) -> list:
        """
        Add additional information to the create option on how the object is
        going to be created.
        """
        create_option = super().build_create_option(q)
        vorname, nachname, kuerzel = parse_autor_name(q)
        create_option.extend(
            [
                # 'id': None will make the option unavailable for selection.
                {'id': None, 'create_id': True, 'text': '...mit folgenden Daten:'},
                {'id': None, 'create_id': True, 'text': f'Vorname: {vorname}'},
                {'id': None, 'create_id': True, 'text': f'Nachname: {nachname}'},
                {'id': None, 'create_id': True, 'text': f'Kürzel: {kuerzel}'},
            ]
        )
        return create_option


class ACBand(ACTabular):
    model = _models.Band
    overview_annotations = ('alias_list', 'orte_list')

    def get_group_headers(self) -> list:
        return ['Alias', 'Orte']

    def get_extra_data(self, result: _models.Band) -> list:
        # noinspection PyUnresolvedReferences
        return [result.alias_list, result.orte_list]


class ACBuchband(ACBase):
    """
    Autocomplete view that queries buch instances that are defined as buchband.
    """

    model = _models.Buch
    queryset = _models.Buch.objects.filter(is_buchband=True)


class ACLagerort(ACTabular):
    # TODO: enable the use of this view (admin.BestandInLine) once it's clear
    #   what fields Lagerort should have and how the default result label
    #   (here: Lagerort._name) should look like

    model = _models.Lagerort

    def get_group_headers(self) -> list:
        return ['Ort', 'Raum']  # pragma: no cover

    def get_extra_data(self, result: _models.Lagerort) -> list:
        # noinspection PyUnresolvedReferences
        # NOTE: the model does not provide overview annotations
        return [result.ort, result.raum]  # pragma: no cover


class ACMagazin(ACBase):
    model = _models.Magazin

    def get_search_results(self, queryset: QuerySet, search_term: str) -> QuerySet:
        # Check if q is a valid ISSN; if it is, compact-ify it.
        if issn.is_valid(search_term):
            search_term = issn.compact(search_term)
        return super().get_search_results(queryset, search_term)


class ACMusiker(ACTabular):
    model = _models.Musiker
    overview_annotations = ('alias_list', 'orte_list')

    def get_group_headers(self) -> list:
        return ['Alias', 'Orte']

    def get_extra_data(self, result: _models.Band) -> list:
        # noinspection PyUnresolvedReferences
        return [result.alias_list, result.orte_list]


class ACPerson(ACBase):
    model = _models.Person
    create_field = '__any__'

    def create_object(self, text: str) -> _models.Person:
        """
        Create an object given a text.

        Add an addition LogEntry to the django admin log table for the created
        object.
        """
        vorname, nachname = parse_name(text)
        obj = self.model.objects.create(vorname=vorname, nachname=nachname)
        log_addition(self.request.user.pk, obj)
        return obj

    def build_create_option(self, q: str) -> list:
        """
        Add additional information to the create option on how the object is
        going to be created.
        """
        create_option = super().build_create_option(q)
        vorname, nachname = parse_name(q)
        create_option.extend(
            [
                # 'id': None will make the option unavailable for selection.
                {'id': None, 'create_id': True, 'text': '...mit folgenden Daten:'},
                {'id': None, 'create_id': True, 'text': f'Vorname: {vorname}'},
                {'id': None, 'create_id': True, 'text': f'Nachname: {nachname}'},
            ]
        )
        return create_option


class ACSpielort(ACTabular):
    model = _models.Spielort

    def get_group_headers(self) -> list:
        return ['Ort']

    def get_extra_data(self, result: _models.Spielort) -> list:
        return [str(result.ort)]


class ACVeranstaltung(ACTabular):
    model = _models.Veranstaltung

    def get_group_headers(self) -> list:
        return ['Datum', 'Spielort']

    def get_extra_data(self, result: _models.Veranstaltung) -> list:
        return [str(result.datum), str(result.spielort)]


class UserAutocompleteView(autocomplete.Select2QuerySetView):
    queryset = get_user_model().objects.order_by('username')
    model_field_name = 'username'


class ContentTypeAutocompleteView(autocomplete.Select2QuerySetView):
    model = ContentType
    model_field_name = 'model'
    admin_site = miz_site

    def get_queryset(self) -> QuerySet:
        """Limit the queryset to models registered with miz_site."""
        apps = [m._meta.app_label for m in self.admin_site._registry.keys()]
        models = [m._meta.model_name for m in self.admin_site._registry.keys()]
        return super().get_queryset().filter(model__in=models, app_label__in=apps).order_by('model')


###############################################################################
# GND (german national library) autocomplete view & paginator.
###############################################################################


class GNDPaginator(Paginator):
    """
    Paginator for autocomplete views that query the German national library.

    Responses send back by the library are already paginated; the
    ``object_list`` will always be of a fixed length (default length: 10).
    Whereas a default paginator would try to slice the object_list to get the
    desired page, the request to the SRU API must define the number/index of
    the starting record of the slice such that the SRU backend sends back the
    correct page.

    Attributes:
        total_count: the total number of records found across all pages
    """
    total_count: int

    def __init__(self, *args: Any, total_count: int = 0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.total_count = total_count

    def page(self, number: int) -> Page:
        """Return a Page object for the given 1-based page number."""
        # Paginator.page would slice the object_list here, but in our case
        # pagination is done by the SRU backend: we only ever get one page thus
        # slicing must not occur.
        return self._get_page(self.object_list, number, self)

    @cached_property
    def count(self) -> int:
        """Return the total number of objects, across all pages."""
        return self.total_count


class GND(autocomplete.Select2QuerySetView):
    """Autocomplete view that queries the SRU API endpoint of the DNB."""

    paginate_by = 10  # DNB default number of records per request
    paginator_class = GNDPaginator

    @staticmethod
    def get_query_string(q: str) -> str:
        """Construct and return a SRU compliant query string."""
        if not q:
            return ""
        query = " and ".join("PER=%s" % w for w in q.split())
        query += " and BBG=Tp*"
        return query

    def get_result_value(self, result: Tuple[str, str]) -> str:
        """Return the value/id of a result."""
        return result[0]

    def get_result_label(self, result: Tuple[str, str]) -> str:
        """Return the label of a result."""
        return f"{result[1]} ({result[0]})"

    def get_queryset(self) -> List[Tuple[str, str]]:
        """Get a list of records from the SRU API."""
        # Calculate the 'startRecord' parameter for the request.
        # The absolute record position of the first record of a page is given by
        #   (page_number -1) * records_per_page
        # Add +1 to account for SRU indexing starting at 1 (instead of at 0).
        page = self.kwargs.get(self.page_kwarg) or self.request.GET.get(self.page_kwarg) or 1
        page_number = int(page)
        start = (page_number - 1) * self.paginate_by + 1

        results, self.total_count = searchgnd(
            query=self.get_query_string(self.q),
            startRecord=[str(start)],
            maximumRecords=[str(self.paginate_by)],
            **self.get_query_func_kwargs()
        )
        return results

    def get_paginator(self, *args: Any, **kwargs: Any) -> GNDPaginator:
        kwargs['total_count'] = self.total_count
        return super().get_paginator(*args, **kwargs)

    # noinspection PyMethodMayBeStatic
    def get_query_func_kwargs(self, **kwargs: Any) -> dict:
        """Hook to insert call kwargs for the query func in get_queryset."""
        return kwargs
