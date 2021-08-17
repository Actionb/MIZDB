from django import http
from django.contrib.auth import get_permission_codename
from django.core.paginator import Paginator
from django.utils.functional import cached_property
from django.utils.translation import gettext

from dal import autocomplete

from dbentry import models as _models
from dbentry.ac.creator import Creator
from dbentry.utils.models import get_model_from_string
from dbentry.utils.admin import log_addition
from dbentry.utils.gnd import searchgnd


class ACBase(autocomplete.Select2QuerySetView):
    """Base view for the autocomplete views of the dbentry app."""

    def dispatch(self, *args, **kwargs):
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            self.model = get_model_from_string(model_name)
        if self.create_field is None:
            self.create_field = kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)

    def has_create_field(self):
        if self.create_field:
            return True
        return False

    def display_create_option(self, context, q):
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if self.has_create_field() and q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                return True
        return False

    def build_create_option(self, q):
        return [{
            'id': q,
            'text': gettext('Create "%(new_value)s"') % {'new_value': q},
            'create_id': True,
        }]

    def get_create_option(self, context, q):
        """Form the correct create_option to append to results."""
        if (self.display_create_option(context, q)
                and self.has_add_permission(self.request)):
            return self.build_create_option(q)
        return []

    def do_ordering(self, queryset):
        """
        Apply ordering to the queryset.

        Use the model's default ordering if the view's get_ordering method does
        not return anything to order with.
        """
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            return queryset.order_by(*ordering)
        return queryset.order_by(*self.model._meta.ordering)

    def apply_q(self, qs):
        """Filter the given queryset 'qs' with the view's search term 'q'."""
        if self.q:
            return qs.find(self.q)
        else:
            return qs

    def create_object(self, text):
        """Create an object given a text."""
        text = text.strip()
        obj = self.model.objects.create(**{self.create_field: text})
        if obj and self.request:
            log_addition(self.request.user.pk, obj)
        return obj

    def get_queryset(self):
        """Return the ordered and filtered queryset for this view."""
        if self.queryset is None:
            qs = self.model.objects.all()
        else:
            qs = self.queryset

        if self.forwarded:
            forward_filter = {}
            for k, v in self.forwarded.items():
                # Remove 'empty' forward items.
                if k and v:
                    forward_filter[k] = v
            if not forward_filter:
                # All forwarded items were empty; return an empty queryset.
                return self.model.objects.none()
            qs = qs.filter(**forward_filter)

        qs = self.do_ordering(qs)
        qs = self.apply_q(qs)
        return qs

    def has_add_permission(self, request):
        """Return True if the user has the permission to add a model."""
        if not request.user.is_authenticated:
            return False
        # At this point, dal calls get_queryset() to get the model options via
        # queryset.model._meta which is unnecessary for ACBase since it
        # declares the model class during dispatch().
        opts = self.model._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def get_result_value(self, result):
        """Return the value of a result."""
        if isinstance(result, (list, tuple)):
            if result[0] == 0:
                # The list 'result' contains the IDs of the results.
                # A '0' ID may be the 'weak hits' separator
                # (query.PrimaryFieldsSearchQuery).
                # Set it's id to None to make it not selectable.
                return None
            return result[0]
        return str(result.pk)

    def get_result_label(self, result):
        """Return the label of a result."""
        if isinstance(result, (list, tuple)):
            return result[1]
        return str(result)


class ACBuchband(ACBase):
    """
    Autocomplete view that queries buch instances that are defined as 'buchband'.
    """

    model = _models.Buch
    queryset = _models.Buch.objects.filter(is_buchband=True)


class ACAusgabe(ACBase):
    """
    Autocomplete view for the model ausgabe that applies chronologic order to
    the results.
    """

    model = _models.Ausgabe

    def do_ordering(self, queryset):
        return queryset.chronologic_order()


class ACCreateable(ACBase):
    """
    Add additional information to the create_option part of the response and
    enable a more involved model instance creation process by utilizing a
    Creator helper object.
    """

    @property
    def creator(self):
        if not hasattr(self, '_creator'):
            self._creator = Creator(self.model, raise_exceptions=False)
        return self._creator

    def createable(self, text, creator=None):
        """
        Return True if a new(!) model instance would be created from 'text'.
        """
        creator = creator or self.creator
        created = creator.create(text, preview=True)
        pk = getattr(created.get('instance', None), 'pk', None)
        if created and pk is None:
            return True
        return False

    def display_create_option(self, context, q):
        """
        Return a boolean whether the create option should be displayed or not.
        """
        if q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):
                # See if we can create a new object from q.
                # If pre-existing objects can be found using q, the create
                # option should not be enabled.
                if self.createable(q):
                    return True
        return False

    def build_create_option(self, q):
        """
        Add additional information on how the object is going to be created
        to the create option.
        """
        create_option = super().build_create_option(q)
        create_info = self.get_creation_info(q)
        if create_info:
            create_option.extend(create_info)
        return create_option

    def get_creation_info(self, text, creator=None):
        """
        Build template context to display a more informative create option.
        """
        def flatten_dict(_dict):
            rslt = []
            for k, v in _dict.items():
                if not v or k == 'instance':
                    continue
                if isinstance(v, dict):
                    rslt.extend(flatten_dict(v))
                else:
                    rslt.append((k, v))
            return rslt

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

    def create_object(self, text, creator=None):
        """Create a model instance from 'text' and save it to the database."""
        text = text.strip()
        if self.has_create_field():
            return super().create_object(text)
        creator = creator or self.creator
        return creator.create(text, preview=False).get('instance')

    def post(self, request):
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
        except:
            msg = 'Erstellung fehlgeschlagen. Bitte benutze den "Hinzufügen" Knopf.'
            return http.JsonResponse({'id': 0, 'text': msg})

        return http.JsonResponse({'id': result.pk, 'text': str(result)})


class GNDPaginator(Paginator):

    def __init__(self, *args, total_count=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_count = total_count

    def page(self, number):
        """Return a Page object for the given 1-based page number."""
        # Paginator.page slices the object_list here, but in our case,
        # pagination is done by the SRU backend: we only ever get one page thus
        # slicing must not occur.
        return self._get_page(self.object_list, number, self)

    @cached_property
    def count(self):
        """Return the total number of objects, across all pages."""
        return self.total_count


class GND(ACBase):
    """
    Autocomplete view that queries the SRU API endpoint of the DNB.
    """

    paginate_by = 10  # DNB default number of records per request
    paginator_class = GNDPaginator

    def get_query_string(self, q=None):
        """Construct and return a SRU compliant query string."""
        if q is None:
            q = self.q
        if not q:
            return ""
        query = " and ".join("PER=%s" % w for w in q.split())
        query += " and BBG=Tp*"
        return query

    def get_result_label(self, result):
        """Return the label of a result."""
        return "%s (%s)" % (result[1], result[0])

    def get_queryset(self):
        """Get a list of records from the SRU API."""
        # Calculate the 'startRecord' parameter for the request.
        # The absolute record position of the first record of a page is given by
        #   (page_number -1) * records_per_page
        # Add +1 to account for SRU indexing starting at 1 (instead of at 0).
        page = self.kwargs.get(self.page_kwarg) or self.request.GET.get(self.page_kwarg) or 1
        page_number = int(page)
        start = (page_number - 1) * self.paginate_by + 1

        results, self.total_count = searchgnd(
            self.get_query_string(self.q),
            startRecord=[str(start)],
            maximumRecords=[str(self.paginate_by)]
            # TODO: support all searchgnd parameters
        )
        return results

    def get_paginator(self, *args, **kwargs):
        kwargs['total_count'] = self.total_count
        return super().get_paginator(*args, **kwargs)
