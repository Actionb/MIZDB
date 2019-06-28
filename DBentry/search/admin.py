from urllib.parse import parse_qsl, urlparse, urlunparse

from django.contrib.admin.views.main import SEARCH_VAR
from django.db.models.query import QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.http import HttpResponseRedirect, QueryDict
from django.urls import reverse

from DBentry.search.forms import searchform_factory, MIZAdminSearchForm

class AdminSearchFormMixin(object):
    
    #TODO: change_list_template attribute
    #TODO: what if we dont want a search_form?
    
    search_form_kwargs = None
    search_form_class = None
    search_form_wrapper = None # Wrapper class such as django admin's AdminForm wrapper
    
    def has_search_form(self):
        #TODO: what's the best attribute to determine that a search_form is wanted?
        return self.search_form_kwargs is not None

    def get_search_form_class(self, **kwargs):
        if self.search_form_class is not None:
            return self.search_form_class
        factory_kwargs = self.search_form_kwargs or {}
        factory_kwargs.update(kwargs)
        return searchform_factory(model = self.model, **factory_kwargs)

    def get_search_form(self, **form_kwargs):
        form_class = self.get_search_form_class()
        form = form_class(**form_kwargs)
        if callable(self.search_form_wrapper):
            form = self.search_form_wrapper(form)
        self.search_form = form
        return form
        
    def changelist_view(self, request, extra_context = None):
        if extra_context is None: extra_context = {}
        search_form = self.get_search_form(initial = request.GET)
        extra_context['advanced_search_form'] = search_form
        extra_context['search_var'] = SEARCH_VAR
        response = super().changelist_view(request, extra_context)
        self.update_changelist_context(response)
        return response
        
    def update_changelist_context(self, response, **kwargs):
        """
        A hook that allows changing the context data of the changelist response after it 
        has been created by changelist_view().
        """
        if not isinstance(response.context_data, dict):
            return response
        if hasattr(self, 'search_form'):
            response.context_data['media'] += self.search_form.media
        response.context_data.update(**kwargs)
        return response       
        
    def lookup_allowed(self, lookup, value):
        if self.has_search_form():
            # allow lookups defined in advanced_search_form
            #TODO: adjust this to the new advanced_search_form!
            for field_list in getattr(self, 'advanced_search_form').values():
                if lookup in field_list:
                    return True
                # the lookup may look like this: field_name__lookup, single out the field_name and try again
                if LOOKUP_SEP in lookup and lookup.rsplit(LOOKUP_SEP, 1)[0] in field_list:
                    return True
        return super().lookup_allowed(lookup, value)    
        
#    def get_preserved_filters(self, request):
#        """
#        Update the querystring for the changelist with possibly new date from the form the user has 
#        sent.
#        """
#        #FIXME: FIX THIS!!
#        preserved_filters =  super().get_preserved_filters(request) #'_changelist_filters=ausgabe__magazin%3D326%26ausgabe%3D14962'
#
#        if not (request.POST and '_changelist_filters' in request.GET):
#            # Either this is request has no POST or no filters were used on the changelist
#            return preserved_filters
#            
#        # Decode the preserved_filters string to get the keys and values that were used to filter with back
#        filter_items = parse_cl_querystring(preserved_filters)
#        for k, v in filter_items.copy().items():
#            if k in request.POST and request.POST[k]:
#                # This changelist filter shows up in request.POST, the user may have changed its value
#                filter_items[k] = request.POST[k] 
#            
#            # Flatten the lists of values
#            if isinstance(filter_items[k], list) and len(filter_items[k]) == 1:
#                filter_items[k] = filter_items[k][0]
#        preserved_filters = parse_qs(preserved_filters) 
#        preserved_filters['_changelist_filters'] = urlencode(sorted(filter_items.items()))
#        return urlencode(preserved_filters)
        
        
    def get_changeform_initial_data(self, request):
        """ Turn _changelist_filters string into a useable dict of field_path:value
            so we can fill some formfields with initial values later on. 
            IMPORTANT: THIS ONLY GOVERNS FORMFIELDS FOR ADD-VIEWS. 
            Primarily used for setting ausgabe/magazin for Artikel add-views.
        """
        initial = super().get_changeform_initial_data(request)
        if '_changelist_filters' not in initial or not initial['_changelist_filters']:
            return initial
            
        # At this point, _changelist_filters is a string of format:
        # '_changelist_filters': 'ausgabe__magazin=47&ausgabe=4288'
        # SEARCH_TERM_SEP: '='
        filter_dict = {}
        for part in initial['_changelist_filters'].split('&'):
            if part and SEARCH_TERM_SEP in part:
                if part.startswith("q="):
                    # This part is a string typed into the searchbar, ignore it
                    continue
                try:
                    k, v = part.split(SEARCH_TERM_SEP)
                except ValueError:
                    continue
                if k not in initial:
                    filter_dict[k] = v
        initial.update(filter_dict)
        return initial       
        
    def _response_post_save(self, request, obj):
        """
        django's helper method that returns the user back to the changelist (or index if no perms).
        In its original form, the method uses 
        django.contrib.admin.templatetags.admin_urls.add_preserved_filters
        to tack on the changelist filters to the redirect url.
        (add_preserved_filters is also used to modify the links of result items)
        But add_preserved_filters drops multiple values from a SelectMultiple by 
        calling dict() on a parsed querystring with multiple values.
        
        To preserve all the filters, we must readd these dropped values to the query string.
        """
        preserved_filters = self.get_preserved_filters(request)
        preserved_filters = dict(parse_qsl(preserved_filters))
        response = super()._response_post_save(request, obj)
        if not self.has_view_or_change_permission(request) or \
            '_changelist_filters' not in preserved_filters:
            # Redirects back to the index or no changelist filters were preserved;
            # no need to act.
            return response
        post_url = response.url
        parsed_url = urlparse(post_url)
        post_url_query = QueryDict(parsed_url.query, mutable = True)
        # Update the query string with any lists that preserved_filters contains.
        for lookup, values_list in QueryDict(preserved_filters['_changelist_filters']).lists():
            if lookup in post_url_query:
                post_url_query.setlist(lookup, values_list)
        # Add the update query string to the url.
        parsed_url = list(parsed_url)
        parsed_url[4] = post_url_query.urlencode()
        post_url = urlunparse(parsed_url)
        return HttpResponseRedirect(post_url)
        
class MIZAdminSearchFormMixin(AdminSearchFormMixin):
    
    def get_search_form_class(self, **kwargs):
        kwargs['form'] = MIZAdminSearchForm
        return super().get_search_form_class(**kwargs)
        
class ChangelistSearchFormMixin(object):
    
    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params)
        try:
            form = self.model_admin.get_search_form(data = params)
        except AttributeError:
            # model_admin does not have the get_search_form method;
            # most likely, the ModelAdmin does not include the 
            # advanced_search_form mixin.
            return lookup_params
        # Preliminarily remove all params that belong to the search form
        # so that, if the form is invalid, the form's data is not 
        # going to be used to filter the changelist's queryset.
        #NOTE: should form.clean do this? 
        for field_name in form.fields:
            if field_name in lookup_params: 
                del lookup_params[field_name]
                
        lookup_params.update(form.get_filter_params())
        return lookup_params
        
    
