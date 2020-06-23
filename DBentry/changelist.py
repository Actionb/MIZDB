from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.db import models
from django.utils.datastructures import MultiValueDict

from DBentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):

    def get_queryset(self, request):
        """
        Copy pasted from django's ChangeList to switch around ordering and
        filtering. Also allow the usage of Q items to filter the queryset.
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
                            qs = qs.filter(**{key: value})
            else:
                # NOTE: isn't remaining_lookup_params always a MultiValueDict?
                for k, v in remaining_lookup_params.items():
                    if isinstance(v, models.Q):
                        qs = qs.filter(v)
                    else:
                        qs = qs.filter(**{k: v})

        except (SuspiciousOperation, ImproperlyConfigured):
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise admin.options.IncorrectLookupParameters(e)

        if not qs.query.select_related:
            qs = self.apply_select_related(qs)

        # Apply search results
        qs, search_use_distinct = self.model_admin.get_search_results(
            request, qs, self.query
        )

        # Get ordering, record and apply annotations and then set the ordering.
        ordering = self.get_ordering(request, qs)
        qs = self.apply_ordering(request, qs, ordering)

        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs

    def apply_ordering(self, request, queryset, ordering):
        return queryset.order_by(*ordering)


class AusgabeChangeList(MIZChangeList):

    def apply_ordering(self, request, queryset, ordering):
        return queryset.chronologic_order(ordering)
