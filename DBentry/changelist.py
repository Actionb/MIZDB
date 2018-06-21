
from django.contrib.admin.views.main import *
from django.utils.datastructures import MultiValueDict

class MIZChangeList(ChangeList):
    
    def __init__(self, request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin):
        super(MIZChangeList, self).__init__(request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin)
        # Save the request (in its QueryDict form) so asf_tag.advanced_search_form(cl) can access it
        self.request = request
        
    def get_filters_params(self, params=None):
        """
        Returns all params except IGNORED_PARAMS
        """
        lookup_params = super(MIZChangeList, self).get_filters_params(params)
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
        # BulkViews redirect
        if request.session.get('qs', {}):
            qs = self.root_queryset.filter(**request.session.get('qs'))
            #TODO: keep the qs if you want to return to the filtered changelist? Example: bulk_ausgabe-> edit created -> merge created -> abort -> back to edit created and not the entire cl
            del request.session['qs']
            return qs
        
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
                # NOTE isn't remaining_lookup_params always a MultiValueDict?
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
        
        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)

        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs
            
    def get_query_string(self, new_params=None, remove=None):
        # Allow the use of '__in' lookup in the query string
        if new_params is None: new_params = {}
        if remove is None: remove = []
        p = self.params.copy()
        for r in remove:
            for k in list(p):
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                if k in p and '__in' in k:
                    in_list = p[k].split(',')
                    if not v in in_list:
                        in_list.append(v)
                    else:
                        in_list.remove(v)
                    p[k] = ','.join(in_list)
                else:
                    p[k] = v
        return '?%s' % urlencode(sorted(p.items()))

class AusgabeChangeList(MIZChangeList):
    
    def get_queryset(self, request):
        from DBentry.models import magazin
        from itertools import chain
        from django.db.models import Count, Sum, Min, Max
        queryset = super().get_queryset(request).order_by() #NOTE: we can keep the querystring order this way
        
        # Get the ordering set either by ModelAdmin.get_ordering/CL._get_default_ordering 
        # or (overriding the previous two) the ordering given by a query string.
        # The primary key is also appended to the end.
        ordering = self.get_ordering(request, queryset) #NOTE: haven't we done this through the call to super() already?
        if not queryset.exists() or not queryset.query.where.children:
            # Don't bother if queryset is empty or not filtered in any way
            return queryset.order_by(*ordering) # django would warn about an unordered list even it was empty
            
        pk_order_item = ordering.pop(-1)
        for o in ['magazin', 'jahr', 'jahrgang', 'sonderausgabe']: #NOTE: jahrgang -> jahr?
            if o not in ordering:
                ordering.append(o)
                
        # Determine if jahr and/or jahrgang should be in ordering. 
        # The overall order may be messed up if the queryset is a mixed bag of records of having both, having neither and having one or the other.
        jj_values = list(queryset.values_list('ausgabe_jahr', 'jahrgang'))
        jahr_values, jahrgang_values = zip(*jj_values) # zip(*list) is the inverse of zip(list)
        jahr_missing = jahr_values.count(None)
        jahrgang_missing = jahrgang_values.count(None)
        
        if jahr_missing and jahrgang_missing:
            # Some records in queryset are missing jahr while others are missing jahrgang
            if jahr_missing > jahrgang_missing:
                # there are more records missing jahr than there are records missing jahrgang
                ordering.remove('jahr')
            elif jahrgang_missing > jahr_missing:
                ordering.remove('jahrgang')
            else:
                # the records are missing an equal amount of either criteria, remove them both
                ordering.remove('jahr')
                ordering.remove('jahrgang')
        elif jahr_missing:
            ordering.remove('jahr')
        elif jahrgang_missing:
            ordering.remove('jahrgang')
        
        # Find the best criteria to order with, which might be either: num, lnum, monat or e_datum
        # Count the presence of the different criteria and sort them accordingly.
        # Account for the joins by taking each sum individually.
        counted = dict(chain(
            queryset.annotate(c = Count('ausgabe_num')).aggregate(num__sum = Sum('c')).items(), 
            queryset.annotate(c = Count('ausgabe_lnum')).aggregate(lnum__sum = Sum('c')).items(), 
            queryset.annotate(c = Count('ausgabe_monat')).aggregate(monat__sum = Sum('c')).items(), 
            queryset.annotate(c = Count('e_datum')).aggregate(e_datum__sum = Sum('c')).items(), 
        ))
        
        criteria = sorted(counted.items(), key = lambda itemtpl: itemtpl[1], reverse = True)
        result_ordering = [sum_name.split('__')[0] for sum_name, sum in criteria]
        ordering.extend(result_ordering + [pk_order_item])
        
        queryset = queryset.annotate(
            jahr = Min('ausgabe_jahr__jahr'), 
            num = Max('ausgabe_num__num'), 
            lnum = Max('ausgabe_lnum__lnum'), 
            monat = Max('ausgabe_monat__monat__ordinal'), 
        ).order_by(*ordering)
        return queryset
