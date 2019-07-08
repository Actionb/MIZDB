from urllib.parse import parse_qsl, urlparse, urlunparse

from django.contrib.admin.templatetags.admin_list import search_form as search_form_tag_context
from django.db.models.constants import LOOKUP_SEP
from django.http import HttpResponseRedirect, QueryDict

from DBentry.search.utils import get_fields_and_lookups_from_path, strip_lookups_from_path
from DBentry.search.forms import searchform_factory, MIZAdminSearchForm

class AdminSearchFormMixin(object):
    
    change_list_template = 'admin/change_list.html'
    
    search_form_kwargs = None
    search_form_class = None
    
    def has_search_form(self):
        return bool(self.search_form_kwargs)

    def get_search_form_class(self, **kwargs):
        if self.search_form_class is not None:
            return self.search_form_class
        factory_kwargs = self.search_form_kwargs or {}
        factory_kwargs.update(kwargs)
        return searchform_factory(model = self.model, **factory_kwargs)

    def get_search_form(self, **form_kwargs):
        form_class = self.get_search_form_class()
        self.search_form = form_class(**form_kwargs)
        return self.search_form
        
    def changelist_view(self, request, extra_context = None):
        if extra_context is None: extra_context = {}
        search_form = self.get_search_form(data = request.GET)
        extra_context['advanced_search_form'] = search_form
        response = super().changelist_view(request, extra_context)
        self.update_changelist_context(response)
        return response
        
    def update_changelist_context(self, response, **kwargs):
        """
        A hook that allows changing the context data of the changelist response after it 
        has been created by changelist_view().
        """
        if not hasattr(response, 'context_data') or not isinstance(response.context_data, dict):
            return response
        if hasattr(self, 'search_form'):
            response.context_data['media'] += self.search_form.media
        # django's search form tag adds some more context items
        if 'cl' in response.context_data:
            extra = search_form_tag_context(response.context_data['cl'])
            response.context_data.update(extra)
        response.context_data.update(kwargs)
        return response       
        
    def lookup_allowed(self, lookup, value):
        allowed = super().lookup_allowed(lookup, value)
        if allowed or not hasattr(self, 'search_form'):
            # super() determined the lookup is allowed or 
            # this model admin has no search form instance set:
            # no reason to dig deeper.
            return allowed
        # Allow lookups defined in advanced_search_form
        # Extract the lookups from the field_path 'lookup'.
        _, lookups = get_fields_and_lookups_from_path(self.model, lookup)
        # Remove all lookups from the field_path to end up with just a relational path.
        field_path = strip_lookups_from_path(lookup, lookups)
        # Now check that the field_path is in the form's fields and 
        # that the lookups are part of that field's registered lookups.        
        return (field_path in self.search_form.fields) and \
            (set(lookups).issubset(self.search_form.lookups.get(field_path, [])))
        
    def get_changeform_initial_data(self, request):
        """ 
        Add data from the changelist filters to the add-form's initial.
        """
        initial = super().get_changeform_initial_data(request)
        if '_changelist_filters' not in initial or not initial['_changelist_filters']:
            return initial
        
        changelist_filters = QueryDict(initial['_changelist_filters'])
        if self.has_search_form():
            # Derive initial values directly from the processed search form data.
            form = self.get_search_form(data=changelist_filters)
            changelist_filters = form.get_filters_params()
            
        # let the intended initial overwrite the filters
        initial = {**changelist_filters, **initial}
        return changelist_filters
        
    def _response_post_save(self, request, obj):
        """
        django's helper method that returns the user back to the changelist (or index if no perms).
        In its original form, the method uses 
        django.contrib.admin.templatetags.admin_urls.add_preserved_filters
        to tack on the changelist filters to the redirect url.
        (add_preserved_filters is also used to modify the links of result items)
        However, add_preserved_filters drops multiple values from a SelectMultiple by 
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
        
    def check(self,  **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_search_form_fields(**kwargs))
        return errors
    
    def _check_search_form_fields(self, **kwargs):
        # local imports in case I decide to remove this check later
        from django.core import exceptions
        from DBentry.search.utils import get_dbfield_from_path
        from django.core import checks
        if not self.has_search_form():
            return []
        errors = []
        for field_path in self.search_form_kwargs.get('fields', []):
            msg =  "Ignored '{model_admin}' search form field: '{field}'. %s."
            msg = msg.format(model_admin = self.__class__.__name__, field = field_path)
            try:
                get_dbfield_from_path(self.model, field_path)
            except exceptions.FieldDoesNotExist:
                errors.append(checks.Info(msg % "Field does not exist"))
            except exceptions.FieldError:
                errors.append(checks.Info(msg % "Field is a reverse relation"))
        return errors
        
class MIZAdminSearchFormMixin(AdminSearchFormMixin):
    
    def get_search_form_class(self, **kwargs):
        kwargs['form'] = MIZAdminSearchForm
        return super().get_search_form_class(**kwargs)
        
class ChangelistSearchFormMixin(object):
    
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(request, *args, **kwargs)
    
    def get_search_form_filters(self, data):
        if not isinstance(self.model_admin, AdminSearchFormMixin):
            return {}
        result = {}
        params = self.model_admin.get_search_form(data = data).get_filters_params()
        for lookup, value in params.items():
            if 'in' in lookup.split(LOOKUP_SEP):
                # Create a string with comma separated values.
                # django admin's prepare_lookup_value() expects an '__in' lookup's value as such.
                result[lookup] = ",".join(str(pk) for pk in value.values_list('pk', flat=True).order_by('pk'))
            else:
                result[lookup] = value
        return result
        
    def get_filters_params(self, params=None):
        if self.request.method == 'POST':
            return {}
        return self.get_search_form_filters(params or self.request.GET)
        
