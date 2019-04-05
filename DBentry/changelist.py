import sys

from django.contrib.admin import FieldListFilter
from django.contrib.admin.exceptions import DisallowedModelAdminLookup
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import get_fields_from_path, lookup_needs_distinct, prepare_lookup_value
from django.contrib.admin.views.main import ChangeList, PAGE_VAR, ERROR_FLAG
from django.db.models import Count

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, SuspiciousOperation
from django.db import models

from django.utils import six
from django.utils.datastructures import MultiValueDict
from django.utils.http import urlencode

class MIZChangeList(ChangeList):
    
    def __init__(self, request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by):
        # Place to store the kwargs for annotations given by an admin_order_field. 
        # Needs to be declared before super().__init__() as get_ordering_field is called during init.
        self._annotations = []
        super(MIZChangeList, self).__init__(request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by)
        # Save the request (in its QueryDict form) so asf_tag.advanced_search_form(cl) can access it
        self.request = request
        
    def get_filters_params(self, params=None):
        """
        Returns all params except IGNORED_PARAMS
        """
        lookup_params = super(MIZChangeList, self).get_filters_params(params).copy()
        # super() does not remove PAGE_VAR and ERROR_FLAG from lookup_params as these are not in IGNORED_PARAMS
        # lookup_params originally defaults to self.params, which already has had PAGE_VAR/ERROR_FLAG removed during init.
        # We are now passing in request.GET instead (to preserve QueryDict functionality), and thus must remove these params again
        # or they will raise an exception in get_queryset.
        if PAGE_VAR in lookup_params:
            del lookup_params[PAGE_VAR]
        if ERROR_FLAG in lookup_params:
            del lookup_params[ERROR_FLAG]
        return lookup_params
    
    def get_filters(self, request):
        # pass request.GET to get_filters_params to get a QueryDict(MultiValueDict) back, this way we can catch multiple values for the same key 
        # which is needed in Advanced Search Form SelectMultiple cases 
        lookup_params = self.get_filters_params(request.GET)
        use_distinct = False
        
        if not lookup_params:
            return [], False, {}, use_distinct
            
        for key, value_list in lookup_params.lists():
            for value in value_list:
                if not self.model_admin.lookup_allowed(key, value):
                    raise DisallowedModelAdminLookup("Filtering by %s not allowed" % key)
            
        filter_specs = []
        if self.list_filter:
            for list_filter in self.list_filter:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(request, lookup_params, self.model, self.model_admin)
                else:
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]

                    lookup_params_count = len(lookup_params)
                    spec = field_list_filter_class(
                        field, request, lookup_params,
                        self.model, self.model_admin, field_path=field_path
                    )
                    # field_list_filter_class removes any lookup_params it
                    # processes. If that happened, check if distinct() is
                    # needed to remove duplicate results.
                    if lookup_params_count > len(lookup_params):
                        use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, field_path)
                if spec and spec.has_output():
                    filter_specs.append(spec)

        # At this point, all the parameters used by the various ListFilters
        # have been removed from lookup_params, which now only contains other
        # parameters passed via the query string. We now loop through the
        # remaining parameters both to ensure that all the parameters are valid
        # fields and to determine if at least one of them needs distinct(). If
        # the lookup parameters aren't real fields, then bail out.
        try:
            # NOTE: if we are not using any list_filter, remaining_lookup_params is equal to lookup_params SANS prepare_lookup_value!
            remaining_lookup_params = MultiValueDict()
            for key, value_list in lookup_params.lists():
                for value in value_list:
                    remaining_lookup_params.appendlist(key, prepare_lookup_value(key, value))
                    use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, key)
            return filter_specs, bool(filter_specs), remaining_lookup_params, use_distinct
        except FieldDoesNotExist as e:
            six.reraise(IncorrectLookupParameters, IncorrectLookupParameters(e), sys.exc_info()[2])
            
    
    def get_queryset(self, request):
        """ Copy pasted from original ChangeList to switch around ordering and filtering.
            Also allowed the usage of Q items to filter the queryset.
        """
        # First, we collect all the declared list filters.
        (self.filter_specs, self.has_filters, remaining_lookup_params,
         filters_use_distinct) = self.get_filters(request)

        # Then, we let every list filter modify the queryset to its liking.
        qs = self.root_queryset
        for filter_spec in self.filter_specs:
            new_qs = filter_spec.queryset(request, qs)
            if new_qs is not None:
                qs = new_qs
        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            if isinstance(remaining_lookup_params, MultiValueDict):
                for key, value_list in remaining_lookup_params.lists():
                    for value in value_list:
                        if isinstance(value, models.Q):
                            qs = qs.filter(value)
                        else:
                            qs = qs.filter(**{key:value})
            else:
                # NOTE: isn't remaining_lookup_params always a MultiValueDict?
                for k, v in remaining_lookup_params.items():
                    if isinstance(v, models.Q):
                        qs = qs.filter(v)
                    else:
                        qs = qs.filter(**{k:v})
                
        except (SuspiciousOperation, ImproperlyConfigured) as e:
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise IncorrectLookupParameters(e)

        if not qs.query.select_related:
            qs = self.apply_select_related(qs)
            
        # Apply search results
        qs, search_use_distinct = self.model_admin.get_search_results(request, qs, self.query)
        
        # Get ordering, record and apply annotations and then set the ordering.
        ordering = self.get_ordering(request, qs)
        qs = self._annotate(qs)
        qs = self.apply_ordering(request, qs, ordering)
        
        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs
            
    def _annotate(self, queryset):
        # Add any pending annotations required for the ordering of callable list_display items to the queryset.
        needs_distinct = False
        if sum(map(len, (self._annotations, queryset.query.annotations))) > 1:
            # If func is Count and there is going to be more than one join, we may need to use distinct = True on all annotations.
            #NOTE: we cannot catch if apply_ordering() is going to add more annotations
            needs_distinct = True
        for annotation in self._annotations:
            name, func, expression, extra = annotation
            if func == Count and needs_distinct and 'distinct' not in extra:
                extra['distinct'] = True
            annotation = {name: func(expression, **extra)}
            queryset = queryset.annotate(**annotation)
        return queryset
        
    def apply_ordering(self, request, queryset, ordering):
        return queryset.order_by(*ordering)
    
    def get_ordering_field(self, field_name):
        # Record any admin_order_field attributes that are meant to be later added as annotations in get_queryset.
        order_field = super().get_ordering_field(field_name)
        if isinstance(order_field, (list, tuple)):
            if len(order_field) != 4:
                raise ImproperlyConfigured("admin_order_field annotations must be a 4-tuple of (name, func, expression, **extra).")
            self._annotations.append(order_field)
            return order_field[0]
        return order_field

class AusgabeChangeList(MIZChangeList):
    
    def apply_ordering(self, request, queryset, ordering):
        return queryset.chronologic_order(ordering)
    
