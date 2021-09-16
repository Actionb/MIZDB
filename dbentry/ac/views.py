from typing import Any, Callable, List, Optional, Sequence, Tuple, Type, Union

# noinspection PyPackageRequirements
from dal import autocomplete
from django import http
from django.contrib.auth import get_permission_codename
from django.core.paginator import Page, Paginator
from django.db.models import Model
from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property
from django.utils.translation import gettext

from dbentry import models as _models
from dbentry.ac.creator import Creator, MultipleObjectsReturned
from dbentry.managers import AusgabeQuerySet, MIZQuerySet
from dbentry.utils.admin import log_addition
from dbentry.utils.gnd import searchgnd
from dbentry.utils.models import get_model_from_string


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

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        """Set model and create_field instance attributes."""
        super().setup(request, *args, **kwargs)
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            if model_name:
                self.model = get_model_from_string(model_name)
        if self.create_field is None:
            self.create_field = kwargs.pop('create_field', None)

    def has_create_field(self) -> bool:
        if self.create_field:
            return True
        return False

    def display_create_option(self, context: dict, q: str) -> bool:
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if self.has_create_field() and q:
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
        # noinspection PyProtectedMember,PyUnresolvedReferences
        return queryset.order_by(*self.model._meta.ordering)  # type: ignore

    def apply_q(self, queryset: MIZQuerySet) -> Union[MIZQuerySet, list]:
        """
        Filter the given queryset with the view's search term ``q``.

        If ``q`` is a numeric value, try a primary key lookup. Otherwise use
        either MIZQuerySet.find to find results or filter against
        ``create_field``, if that is set.

        Returns:
            a list if querying via MIZQuerySet.find or a MIZQuerySet.
        """
        if self.q:
            # If the search term is a numeric value, try using it in a primary
            # key lookup, and if that returns results, return them.
            if self.q.isnumeric() and queryset.filter(pk=self.q).exists():
                return queryset.filter(pk=self.q)
            if isinstance(queryset, MIZQuerySet):
                return queryset.find(self.q)
            elif self.create_field:
                return queryset.filter(**{self.create_field: self.q})
        return queryset

    def create_object(self, text: str) -> Model:
        """
        Create an object given a text.

        If an object was created, add an addition LogEntry to the django admin
        log table.
        """
        text = text.strip()
        # noinspection PyUnresolvedReferences
        obj = self.model.objects.create(**{self.create_field: text})  # type: ignore
        if obj and self.request:
            log_addition(self.request.user.pk, obj)
        return obj

    def get_queryset(self) -> MIZQuerySet:
        """Return the ordered and filtered queryset for this view."""
        if self.queryset is None:
            # noinspection PyUnresolvedReferences
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
                # noinspection PyUnresolvedReferences
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
        # At this point, dal calls get_queryset() to get the model options via
        # queryset.model._meta which is unnecessary for ACBase since it
        # declares the model class during dispatch().
        # noinspection PyProtectedMember, PyUnresolvedReferences
        opts = self.model._meta  # type: ignore
        codename = get_permission_codename('add', opts)
        return user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_result_value(self, result: Union[Model, Sequence]) -> Optional[Union[str, int]]:
        """
        Return the value (usually the primary key) of a result.

        Args:
            result: may be a model instance or a sequence, such as the list
                returned by MIZQuerySet.find().
        """
        if isinstance(result, (list, tuple)):
            if result[0] == 0:
                # The list 'result' contains the IDs of the results.
                # A '0' ID may be the 'weak hits' separator
                # (query.PrimaryFieldsSearchQuery).
                # Set it's id to None to make it not selectable.
                return None
            return result[0]
        return str(result.pk)  # type: ignore

    def get_result_label(self, result: Union[Model, Sequence]) -> str:
        """
        Return the label of a result.

        Args:
            result: may be a model instance or a sequence, such as the list
                returned by MIZQuerySet.find().
        """
        if isinstance(result, (list, tuple)):
            return result[1]
        return str(result)


class ACBuchband(ACBase):
    """
    Autocomplete view that queries buch instances that are defined as buchband.
    """

    model = _models.Buch
    queryset = _models.Buch.objects.filter(is_buchband=True)


class ACAusgabe(ACBase):
    """
    Autocomplete view for the model ausgabe that applies chronological order to
    the results.
    """

    model = _models.Ausgabe

    def do_ordering(self, queryset: AusgabeQuerySet) -> AusgabeQuerySet:
        return queryset.chronological_order()


class ACCreatable(ACBase):
    """
    Add additional information to the create_option part of the response and
    enable a more involved model instance creation process by utilizing a
    Creator helper object.
    """

    @property
    def creator(self):
        if not hasattr(self, '_creator'):
            # noinspection PyAttributeOutsideInit
            self._creator = Creator(self.model, raise_exceptions=False)
        return self._creator

    def creatable(self, text: str, creator: Optional[Creator] = None) -> bool:
        """
        Return True if a new(!) model instance would be created from ``text``.
        """
        creator = creator or self.creator
        created = creator.create(text, preview=True)
        pk = getattr(created.get('instance', None), 'pk', None)
        if created and pk is None:
            return True
        return False

    def display_create_option(self, context: dict, q: str) -> bool:
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                # See if we can create a new object from q.
                # If pre-existing objects can be found using q, the create
                # option should not be enabled.
                if self.creatable(q):
                    return True
        return False

    def build_create_option(self, q: str) -> list:
        """
        Add additional information to the create option on how the object is
        going to be created.
        """
        create_option = super().build_create_option(q)
        create_info = self.get_creation_info(q)
        if create_info:
            create_option.extend(create_info)
        return create_option

    def get_creation_info(self, text: str, creator: Optional[Creator] = None) -> list:
        """
        Build template context to display a more informative create option.
        """

        def flatten_dict(_dict):
            result = []
            for key, value in _dict.items():
                if not value or key == 'instance':
                    continue
                if isinstance(value, dict):
                    result.extend(flatten_dict(value))
                else:
                    result.append((key, value))
            return result

        creator = creator or self.creator
        create_info = []
        default = {
            'id': None,  # 'id': None will make the option not selectable.
            'create_id': True, 'text': '...mit folgenden Daten:'
        }

        create_info.append(default.copy())
        # Iterate over all nested dicts in create_info returned by the creator.
        for k, v in flatten_dict(creator.create(text, preview=True)):
            default['text'] = str(k) + ': ' + str(v)
            create_info.append(default.copy())
        return create_info

    def create_object(self, text: str, creator: Optional[Creator] = None) -> Model:
        """Create a model instance from ``text`` and save it to the database."""
        text = text.strip()
        if self.has_create_field():
            return super().create_object(text)
        creator = creator or self.creator
        return creator.create(text, preview=False).get('instance')

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Create an object given a text after checking permissions."""
        if not self.has_add_permission(request):
            return http.HttpResponseForbidden()

        if not self.creator and not self.create_field:
            raise AttributeError('Missing creator object or "create_field"')

        text = request.POST.get('text', None)

        if text is None:
            return http.HttpResponseBadRequest()

        try:
            result = self.create_object(text)
        except MultipleObjectsReturned:
            msg = 'Erstellung fehlgeschlagen. Bitte benutze den "Hinzufügen" Knopf.'
            return http.JsonResponse({'id': 0, 'text': msg})

        return http.JsonResponse({'id': result.pk, 'text': str(result)})


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
    """
    Autocomplete view that queries the SRU API endpoint of the DNB.

    Attributes:
        sru_query_func: the callable that fetches the results from the endpoint
    """

    paginate_by = 10  # DNB default number of records per request
    paginator_class = GNDPaginator
    sru_query_func: Callable = searchgnd

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

        results, self.total_count = self.sru_query_func(
            self.get_query_string(self.q),
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
