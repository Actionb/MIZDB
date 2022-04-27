from typing import Any, List, Optional, Tuple, Type, Union

# noinspection PyPackageRequirements
from dal import autocomplete
from django import http
from django.contrib.auth import get_permission_codename, get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.core.paginator import Page, Paginator
from django.db.models import Model
from django.http import HttpRequest, HttpResponse
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


def create_person(text: str) -> _models.Person:
    """Get an existing or build a new (unsaved) Person instance from name ``text``."""
    # parse_name will join first and middle names:
    vorname, nachname = parse_name(text)
    try:
        return _models.Person.objects.get(vorname=vorname, nachname=nachname)
    except _models.Person.DoesNotExist:  # noqa
        return _models.Person(vorname=vorname, nachname=nachname)


def create_autor(text: str) -> _models.Autor:
    """Get an existing or build a new (unsaved) Autor instance from name ``text``."""
    # Parse the name through the nameparser to find out the nickname, which
    # will be used as kuerzel. Then pass the name without nickname to the
    # Person constructor.
    name = HumanName(text)
    kuerzel = name.nickname[:8]
    name.nickname = ''
    name = str(name)

    p = None
    if name:
        # Do not create 'nameless' Person instances.
        # (the database would allow this)
        p = create_person(name)

    try:
        kwargs = {'kuerzel': kuerzel}
        if p:
            kwargs.update(person__vorname=p.vorname, person__nachname=p.nachname)
        return _models.Autor.objects.get(**kwargs)
    except _models.Autor.DoesNotExist:  # noqa
        return _models.Autor(kuerzel=kuerzel, person=p)


class ACBase(autocomplete.Select2QuerySetView):
    """
    Base view for the autocomplete views of the dbentry app.

    This class extends Select2QuerySetView in the following ways:
        - set instance attributes ``model`` and ``create_field`` from the
          request payload/keyword arguments
        - split up the process of providing a create option into several
          methods (``get_create_option``)
        - ``get_queryset`` includes forwarded values, and the method calls
          other methods to perform ordering and search term filtering
        - ``get_result_value`` and ``get_result_label`` can handle lists/tuples
    """
    model: Optional[Type[Model]]
    create_field: Optional[str]

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        """Set model and create_field instance attributes."""
        super().setup(request, *args, **kwargs)
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            if model_name:
                self.model = get_model_from_string(model_name)
        if self.create_field is None:
            self.create_field = kwargs.pop('create_field', None)

    def display_create_option(self, context: dict, q: str) -> bool:
        """Return a boolean whether the create option should be displayed."""
        if self.create_field and q is not None and q.strip():
            # Don't offer to create a new option if a case-insensitive
            # identical one already exists.
            existing_options = (self.get_result_label(result).lower()
                                for result in context['object_list'])
            if q.lower() in existing_options:
                return False
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                return True
        return False

    def build_create_option(self, q: str) -> list:
        """Form the create option item to append to the result list."""
        return [{
            'id': q,
            'text': gettext('Create "%(new_value)s"') % {'new_value': q},
            'create_id': True,
        }]

    def get_create_option(self, context: dict, q: str) -> list:
        """Form the correct create_option to append to results."""
        if (self.display_create_option(context, q)
                and self.has_add_permission(self.request)):
            return self.build_create_option(q)
        return []

    def do_ordering(self, queryset: MIZQuerySet) -> MIZQuerySet:
        """
        Apply ordering to the queryset and return it.

        Use the model's default ordering if the view's get_ordering method does
        not return anything to order with.
        """
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            return queryset.order_by(*ordering)
        return queryset.order_by(*self.model._meta.ordering)  # type: ignore

    def apply_q(self, queryset: MIZQuerySet) -> MIZQuerySet:
        """
        Filter the given queryset with the view's search term ``q``.

        If ``q`` is a numeric value, try a primary key lookup. Otherwise, use
        either MIZQuerySet.search to find results.
        """
        if self.q:
            # If the search term is a numeric value, try using it in a primary
            # key lookup, and if that returns results, return them.
            if self.q.isnumeric() and queryset.filter(pk=self.q).exists():
                return queryset.filter(pk=self.q)
            return queryset.search(self.q)
        return queryset

    def create_object(self, text: str) -> Model:
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        text = text.strip()
        obj = self.model.objects.create(**{self.create_field: text})  # type: ignore
        if obj and self.request:
            log_addition(self.request.user.pk, obj)
        return obj

    def get_queryset(self) -> MIZQuerySet:
        """Return the ordered and filtered queryset for this view."""
        if self.queryset is None:
            queryset = self.model.objects.all()  # type: ignore
        else:
            queryset = self.queryset

        if self.forwarded:
            forward_filter = {}
            for k, v in self.forwarded.items():
                # Remove 'empty' forward items.
                if k and v:
                    forward_filter[k] = v
            if not forward_filter:
                # All forwarded items were empty; return an empty queryset.
                return self.model.objects.none()  # type: ignore
            queryset = queryset.filter(**forward_filter)

        queryset = self.do_ordering(queryset)
        queryset = self.apply_q(queryset)
        return queryset

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Return True if the user has the permission to add a model."""
        # noinspection PyUnresolvedReferences
        user = request.user
        if not user.is_authenticated:
            return False
        # dal would call get_queryset() here to get the model options via
        # queryset.model._meta. Since ACBase sets the model class attribute
        # during setup, we can skip calling get_queryset:
        opts = self.model._meta  # type: ignore
        codename = get_permission_codename('add', opts)
        return user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_result_value(self, result: Model) -> Optional[Union[str, int]]:
        """
        Return the value (usually the primary key) of a result model instance.
        """
        if isinstance(result, (list, tuple)):
            return result[0]
        return str(result.pk)  # type: ignore

    def get_result_label(self, result: Model) -> str:
        """Return the label of a result model instance."""
        if isinstance(result, (list, tuple)):
            return str(result[1])
        return str(result)


class ACTabular(ACBase):
    # noinspection GrazieInspection
    """
        Autocomplete view that presents the result data in tabular form.

        Select2 will group the results returned in the JsonResponse into option
        groups (optgroup). This (plus bootstrap grids) will allow useful
        presentation of the data.
        """

    # noinspection PyMethodMayBeStatic
    def get_extra_data(self, result: Model) -> list:
        """Return the additional data to be displayed for the given result."""
        return []

    # noinspection PyMethodMayBeStatic
    def get_group_headers(self) -> list:
        """Return a list of labels for the additional columns/group headers."""
        return []

    def get_results(self, context: dict) -> List[dict]:
        """Return data for the 'results' key of the response."""
        return [
            {
                'id': self.get_result_value(result),
                'text': self.get_result_label(result),
                EXTRA_DATA_KEY: self.get_extra_data(result),
                'selected_text': self.get_selected_result_label(result),
            } for result in context['object_list']
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

            results = [{
                "text": self.model._meta.verbose_name,  # type: ignore[union-attr]
                "children": result_list + create_option,
                "is_optgroup": True,
                "optgroup_headers": headers,
            }]
        else:
            results = result_list + create_option

        return http.JsonResponse(
            {
                'results': results,
                'pagination': {
                    'more': self.has_more(context)
                }
            }
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

    def do_ordering(self, queryset: AusgabeQuerySet) -> AusgabeQuerySet:
        return queryset.chronological_order()

    def get_queryset(self) -> MIZQuerySet:
        queryset = super().get_queryset()
        from dbentry.admin import AusgabenAdmin, miz_site
        model_admin = AusgabenAdmin(self.model, miz_site)
        return queryset.annotate(**model_admin.get_changelist_annotations())

    def get_group_headers(self) -> list:
        return ['Nummer', 'lfd.Nummer', 'Jahr']

    def get_extra_data(self, result: Model) -> list:
        # noinspection PyUnresolvedReferences
        return [result.num_string, result.lnum_string, result.jahr_string]


class ACAutor(ACBase):
    model = _models.Autor
    create_field = '__any__'

    def create_object(self, text: str) -> _models.Autor:
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        obj = create_autor(text.strip())
        # Save the instance or its related Person instance, if either are
        # unsaved.
        if obj.person.pk is None:
            obj.person.save()
            log_addition(self.request.user.pk, obj.person)
        if obj.pk is None:
            obj.save()
            log_addition(self.request.user.pk, obj)
        return obj

    def build_create_option(self, q: str) -> list:
        """
        Add additional information to the create option on how the object is
        going to be created.
        """
        create_option = super().build_create_option(q)
        obj = create_autor(q)
        create_option.extend([
            # 'id': None will make the option unavailable for selection.
            {'id': None, 'create_id': True, 'text': '...mit folgenden Daten:'},
            {'id': None, 'create_id': True, 'text': f'Vorname: {obj.person.vorname}'},
            {'id': None, 'create_id': True, 'text': f'Nachname: {obj.person.nachname}'},
            {'id': None, 'create_id': True, 'text': f'Kürzel: {obj.kuerzel}'},
        ])
        return create_option


class ACBand(ACTabular):
    model = _models.Band

    def get_group_headers(self) -> list:
        return ['Alias']

    def get_extra_data(self, result: Model) -> list:
        # noinspection PyUnresolvedReferences
        return [", ".join(str(alias) for alias in result.bandalias_set.all())]


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
        return ['Ort', 'Raum']

    def get_extra_data(self, result: Model) -> list:
        # noinspection PyUnresolvedReferences
        return [result.ort, result.raum]


class ACMagazin(ACBase):
    model = _models.Magazin

    def apply_q(self, queryset: MIZQuerySet) -> MIZQuerySet:
        # Check if q is a valid ISSN; if it is, remove the dashes.
        if issn.is_valid(self.q):  # type: ignore[has-type]
            self.q = issn.compact(self.q)  # type: ignore[has-type]
        return super().apply_q(queryset)


class ACMusiker(ACTabular):
    model = _models.Musiker

    def get_group_headers(self) -> list:
        return ['Alias']

    def get_extra_data(self, result: Model) -> list:
        # noinspection PyUnresolvedReferences
        return [", ".join(str(alias) for alias in result.musikeralias_set.all())]


class ACPerson(ACBase):
    model = _models.Person
    create_field = '__any__'

    def create_object(self, text: str) -> _models.Person:
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        obj = create_person(text.strip())
        if obj.pk is None:
            obj.save()
            log_addition(self.request.user.pk, obj)
        return obj

    def build_create_option(self, q: str) -> list:
        """
        Add additional information to the create option on how the object is
        going to be created.
        """
        create_option = super().build_create_option(q)
        obj = create_person(q)
        create_option.extend([
            # 'id': None will make the option unavailable for selection.
            {'id': None, 'create_id': True, 'text': '...mit folgenden Daten:'},
            {'id': None, 'create_id': True, 'text': f'Vorname: {obj.vorname}'},
            {'id': None, 'create_id': True, 'text': f'Nachname: {obj.nachname}'},
        ])
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

    def get_queryset(self):
        """Limit the queryset to models registered with miz_site."""
        registered_models = [m._meta.model_name for m in self.admin_site._registry.keys()]
        return super().get_queryset().filter(model__in=registered_models).order_by('model')


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


class GND(ACBase):
    """Autocomplete view that queries the SRU API endpoint of the DNB."""

    paginate_by = 10  # DNB default number of records per request
    paginator_class = GNDPaginator

    def get_query_string(self, q: Optional[str] = None) -> str:
        """Construct and return a SRU compliant query string."""
        if q is None:
            q = self.q
        if not q:
            return ""
        query = " and ".join("PER=%s" % w for w in q.split())
        query += " and BBG=Tp*"
        return query

    def get_result_label(self, result: Tuple[str, str]) -> str:  # type: ignore[override]
        """Return the label of a result."""
        return "%s (%s)" % (result[1], result[0])

    def get_queryset(self) -> List[Tuple[str, str]]:  # type: ignore[override]
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
