from django.contrib import admin
from django.contrib.admin.views.main import ChangeList, PAGE_VAR, ERROR_FLAG
from django.db import models
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, SuspiciousOperation
from django.utils.datastructures import MultiValueDict

from DBentry.search.admin import ChangelistSearchFormMixin

class MIZChangeList(ChangelistSearchFormMixin, ChangeList):
    
    def __init__(self, request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by):
        # Place to store the kwargs for annotations given by an admin_order_field. 
        # Needs to be declared before super().__init__() as get_ordering_field is called during init.
        self._annotations = []
        super(MIZChangeList, self).__init__(request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by)

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
            #TODO: a advsf formfield may throw a ValidationError!
            raise admin.options.IncorrectLookupParameters(e)

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
            if func == models.Count and needs_distinct and 'distinct' not in extra:
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
    
