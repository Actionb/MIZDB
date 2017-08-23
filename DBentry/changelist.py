
from django.contrib.admin.views.main import *

class MIZChangeList(ChangeList):
    
    def get_filters(self, request):
        lookup_params = self.get_filters_params()
        use_distinct = False

        for key, value in lookup_params.items():
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
            remaining_lookup_params = dict()
            for key, value in lookup_params.items():
                if key in self.model_admin.search_fields_redirect:
                    qobject = models.Q()
                    if key in self.model_admin.search_fields_redirect:
                        redirects = self.model_admin.search_fields_redirect.get(key, [])
                        if not isinstance(redirects, (list, tuple)):
                            redirects = [redirects]
                    for redirect in redirects:
                        if callable(redirect):
                            continue
                        qobject |= models.Q( (redirect, prepare_lookup_value(redirect, value)) )
                        use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, redirect)
                    remaining_lookup_params[key] = qobject
                else:
                    remaining_lookup_params[key] = prepare_lookup_value(key, value)
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
       
        qs = qs.resultbased_ordering()
        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)
        
        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs