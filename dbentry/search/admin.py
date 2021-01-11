from urllib.parse import parse_qsl, urlparse, urlunparse

from django.core import checks, exceptions
from django.contrib.admin.templatetags.admin_list import search_form as search_form_tag_context
from django.db.models.lookups import Range, LessThanOrEqual
from django.http import HttpResponseRedirect, QueryDict

from DBentry import utils
from DBentry.search import utils as search_utils
from DBentry.search.forms import searchform_factory, MIZAdminSearchForm


class AdminSearchFormMixin(object):
    """
    A mixin for ModelAdmin classes that adds more search options to its
    changelist.

    Attributes:
        - search_form_kwargs (dict): the keyword arguments for
            searchform_factory to create a search form class with.
            These are *not* the arguments for form initialization!
    """

    change_list_template = 'admin/change_list.html'
    search_form_kwargs = None

    def has_search_form(self):
        """
        Return True if a non-empty search form class was created for this
        instance.

        A search form class would be empty if the instance's
        'search_form_kwargs' did not specify any 'fields'.
        """
        if isinstance(self.search_form_kwargs, dict):
            return bool(self.search_form_kwargs.get('fields'))
        return False

    def get_search_form_class(self, **kwargs):
        """
        Create a form class that will facilitate changelist searches.

        By default, the form class is created by the searchform_factory, using
        'search_form_kwargs' and the kwargs provided as keyword arguments.
        """
        factory_kwargs = self.search_form_kwargs or {}
        factory_kwargs.update(kwargs)
        return searchform_factory(model=self.model, **factory_kwargs)

    def get_search_form(self, **form_kwargs):
        """Instantiate the search form with the given 'form_kwargs'."""
        form_class = self.get_search_form_class()
        self.search_form = form_class(**form_kwargs)
        return self.search_form

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        # Add the search form as 'advanced_search_form' to the extra_context.
        search_form = self.get_search_form(data=request.GET)
        extra_context['advanced_search_form'] = search_form
        response = super().changelist_view(request, extra_context)
        # Let django.admin do its thing, then update the response's context.
        self.update_changelist_context(response)
        return response

    def update_changelist_context(self, response, **kwargs):
        """
        Update the context of the changelist response.

        Add the search form's media to the media context and include other
        context variables required by the advanced_search_form.
        """
        if not hasattr(response, 'context_data'):
            # Not all responses allow access to the template context post
            # instantiation.
            return response
        if hasattr(self, 'search_form') and hasattr(self.search_form, 'media'):
            # Add the search form's media to the context (if this model_admin
            # instance has one).
            if 'media' in response.context_data:
                response.context_data['media'] += self.search_form.media
            else:
                response.context_data['media'] = self.search_form.media
        # django's search_form tag adds context items
        # (show_result_count, search_var) that are also required by the
        # advanced_search_form template. Since the default tag is not called
        # when an advanced_search_form is available, we need to add these
        # context items explicitly.
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
        # Allow lookups defined in advanced_search_form.
        # Extract the lookups from the field_path 'lookup':
        try:
            _, lookups = utils.get_fields_and_lookups(self.model, lookup)
        except (exceptions.FieldDoesNotExist, exceptions.FieldError):
            return False
        # Remove all lookups from the field_path to end up with just a
        # relational path:
        field_path = search_utils.strip_lookups_from_path(lookup, lookups)
        # All lookups that the formfield was registered with should be allowed
        # by default.
        allowed = self.search_form.lookups.get(field_path, [])
        if Range.lookup_name in allowed:
            # If the start of a range is not given, a __lte lookup will be used.
            allowed.append(LessThanOrEqual.lookup_name)
        # Now check that the field_path is in the form's fields and
        # that the lookups are part of that field's registered lookups.
        return (
            field_path in self.search_form.fields
            and set(lookups).issubset(allowed)
        )

    def get_changeform_initial_data(self, request):
        """Add data from the changelist filters to the add-form's initial."""
        initial = super().get_changeform_initial_data(request)
        if '_changelist_filters' not in initial or not initial['_changelist_filters']:
            return initial
        changelist_filters = QueryDict(initial['_changelist_filters'])
        if self.has_search_form():
            # Derive initial values directly from the processed search form data.
            form = self.get_search_form(data=changelist_filters)
            changelist_filters = form.get_filters_params()
        # Let the intended initial overwrite the filters:
        return {**changelist_filters, **initial}

    def _response_post_save(self, request, obj):
        """
        Readd query parameters dropped by add_preserved_filters.

        '_response_post_save' is django's helper method that returns the user
        back to the changelist (or index if no perms) after a save.
        In its original form, the method uses
            django.contrib.admin.templatetags.admin_urls.add_preserved_filters
        to tack on the changelist filters to the redirect url.
        (add_preserved_filters is also used to modify the links of result items)

        However, add_preserved_filters drops multiple values from a SelectMultiple
        by calling dict() on a parsed querystring with multiple values:
            '?_changelist_filters=genre%3D176%26genre%3D594'
        becomes:
            '?genre=176'
        when it should be:
            '?genre=176&genre=594'

        To preserve all the filters, we must readd these dropped values to the
        query string.
        """
        # Get the '_changelist_filters' part of the querystring.
        preserved_filters = self.get_preserved_filters(request)
        preserved_filters = dict(parse_qsl(preserved_filters))
        response = super()._response_post_save(request, obj)
        if (not isinstance(response, HttpResponseRedirect)
                or not self.has_view_or_change_permission(request)
                or '_changelist_filters' not in preserved_filters):
            # Either the response is not a redirect (we need the url attribute) or
            # it redirects back to the index due to missing perms or
            # no changelist filters were preserved.
            return response
        # Extract the query params for the search form from the redirect url.
        post_url = response.url
        parsed_url = urlparse(post_url)
        post_url_query = QueryDict(parsed_url.query, mutable=True)
        # Create a QueryDict mapping search_form fields to
        # lists of *all* their preserved values.
        preserved = QueryDict(preserved_filters['_changelist_filters'])
        for lookup, values_list in preserved.lists():
            if lookup in post_url_query:
                # Replace the list of values for this lookup, thereby
                # adding the values that were dropped by add_preserved_filters.
                post_url_query.setlist(lookup, values_list)
        # Reconstruct the url with the updated query string.
        parsed_url = list(parsed_url)
        parsed_url[4] = post_url_query.urlencode()
        post_url = urlunparse(parsed_url)
        return HttpResponseRedirect(post_url)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_search_form_fields(**kwargs))
        return errors

    def _check_search_form_fields(self, **kwargs):
        """Check the fields given in self.search_form_kwargs."""
        if not self.has_search_form():
            return []
        errors = []
        # Relation fields defined by the model should be in the search form:
        rel_fields = [
            field.name
            for field in utils.get_model_fields(self.model, base=False, foreign=True, m2m=True)
        ]
        for field_path in self.search_form_kwargs.get('fields', []):
            msg = "Ignored search form field: '{field}'. %s".format(field=field_path)
            try:
                search_utils.get_dbfield_from_path(self.model, field_path)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError) as e:
                errors.append(checks.Info(msg % e.args[0], obj=self))
            else:
                try:
                    rel_fields.remove(field_path.split('__')[0])
                except ValueError:
                    # The first part of field_path is not in the rel_fields.
                    pass
        if rel_fields:
            errors.append(
                checks.Info(
                    "Changelist search form is missing fields for relations:"
                    "\n\t%s" % (rel_fields),
                    obj=self
                )
            )
        return errors


class MIZAdminSearchFormMixin(AdminSearchFormMixin):
    """Default mixin for MIZAdmin admin models adding more search options."""

    def get_search_form_class(self, **kwargs):
        # Set the default form class for searchform_factory:
        kwargs['form'] = MIZAdminSearchForm
        return super().get_search_form_class(**kwargs)


class ChangelistSearchFormMixin(object):
    """Mixin for changelist classes to incorporate the new search form."""

    def __init__(self, request, *args, **kwargs):
        # Preserve the contents of request.GET.
        # The changelist attribute 'param' is insufficient as it destroys
        # the multiple values of a MultiValueDict by calling items() instead
        # of lists(): self.params = dict(request.GET.items())
        # django's changelist does not inherit the base View class that sets
        # self.request during setup().
        self.request = request
        super().__init__(request, *args, **kwargs)

    def get_filters_params(self, params=None):
        """Replace the default filter params with those from the search form."""
        params = super().get_filters_params(params)
        if not isinstance(self.model_admin, AdminSearchFormMixin):
            return params
        # If the ModelAdmin instance has a search form, let the form come up
        # with filter parameters.
        # Should the request contain query parameters that a part of the search
        # form, prioritize params returned by the form over the params included
        # in the request.
        search_form_params = self.model_admin.get_search_form(
            data=self.request.GET).get_filters_params()
        if search_form_params:
            return search_form_params
        return params
