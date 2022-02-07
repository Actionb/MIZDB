from typing import Any, List, Optional, Type
from urllib.parse import parse_qsl, urlparse, urlunparse

from django.contrib.admin.templatetags.admin_list import search_form as search_form_tag_context
from django.core import checks, exceptions
from django.db.models import Model
from django.db.models.lookups import LessThanOrEqual, Range
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, QueryDict

from dbentry import utils
from dbentry.search import utils as search_utils
from dbentry.search.forms import MIZAdminSearchForm, SearchForm, searchform_factory


# noinspection PyUnresolvedReferences
class AdminSearchFormMixin(object):
    """
    A mixin for ModelAdmin classes that adds more search options to its
    changelist.

    Attributes:
        - ``search_form_kwargs`` (dict): the keyword arguments for
          searchform_factory to create a search form class with.
          These are *not* the arguments for form initialization!
    """

    change_list_template = 'admin/change_list.html'

    search_form_kwargs: dict = None  # type: ignore[assignment]

    def has_search_form(self) -> bool:
        """
        Return True if a non-empty search form class was created for this
        instance.

        A search form class would be empty if the instance's
        ``search_form_kwargs`` did not specify any fields.
        """
        if isinstance(self.search_form_kwargs, dict):
            return bool(self.search_form_kwargs.get('fields'))
        return False

    def get_search_form_class(self, **kwargs: Any) -> Type[SearchForm]:
        """
        Create a form class that will facilitate changelist searches.

        By default, the form class is created by the searchform_factory, using
        'search_form_kwargs' and the kwargs provided as keyword arguments.
        """
        factory_kwargs = self.search_form_kwargs or {}
        factory_kwargs.update(kwargs)
        return searchform_factory(model=self.model, **factory_kwargs)  # type: ignore[attr-defined]

    def get_search_form(self, **form_kwargs: Any) -> SearchForm:
        """Instantiate the search form with the given 'form_kwargs'."""
        form_class = self.get_search_form_class()
        # noinspection PyAttributeOutsideInit
        self.search_form = form_class(**form_kwargs)
        return self.search_form

    def changelist_view(
            self,
            request: HttpRequest,
            extra_context: Optional[dict] = None
    ) -> HttpResponse:
        if extra_context is None:
            extra_context = {}
        # Add the search form as 'advanced_search_form' to the extra_context.
        search_form = self.get_search_form(data=request.GET)
        extra_context['advanced_search_form'] = search_form
        response = super().changelist_view(request, extra_context)  # type: ignore[misc]
        # Let django.admin do its thing, then update the response's context.
        self.update_changelist_context(response)
        return response

    def update_changelist_context(self, response: HttpResponse, **kwargs: Any) -> HttpResponse:
        """
        Update the context of the changelist response.

        Add the search form's media to the media context and include other
        context variables required by the advanced_search_form.
        """
        if not hasattr(response, 'context_data'):
            # Not all responses allow access to the template context post
            # instantiation.
            return response
        # noinspection PyUnresolvedReferences
        context_data = response.context_data
        if hasattr(self, 'search_form') and hasattr(self.search_form, 'media'):
            # Add the search form's media to the context (if this model_admin
            # instance has one).
            if 'media' in context_data:
                context_data['media'] += self.search_form.media
            else:
                context_data['media'] = self.search_form.media
        # django's search_form tag adds context items
        # (show_result_count, search_var) that are also required by the
        # advanced_search_form template. Since the default tag is not called
        # when an advanced_search_form is available, we need to add these
        # context items explicitly.
        if 'cl' in context_data:
            extra = search_form_tag_context(context_data['cl'])
            context_data.update(extra)
        context_data.update(kwargs)
        return response

    def lookup_allowed(self, lookup: str, value: Any) -> bool:
        allowed = super().lookup_allowed(lookup, value)  # type: ignore[misc]
        if allowed or not hasattr(self, 'search_form'):
            # super() determined the lookup is allowed or
            # this model admin has no search form instance set:
            # no reason to dig deeper.
            return allowed
        # Allow lookups defined in advanced_search_form.
        # Extract the lookups from the field_path 'lookup':
        try:
            _, lookups = utils.get_fields_and_lookups(
                self.model, lookup  # type: ignore[attr-defined]
            )
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

    def get_changeform_initial_data(self, request: HttpRequest) -> dict:
        """Add data from the changelist filters to the add form's initial."""
        initial = super().get_changeform_initial_data(request)  # type: ignore[misc]
        if '_changelist_filters' not in initial or not initial['_changelist_filters']:
            return initial
        changelist_filters = QueryDict(initial['_changelist_filters'])
        if self.has_search_form():
            # Derive initial values directly from the processed search form data.
            form = self.get_search_form(data=changelist_filters)
            changelist_filters = form.get_filters_params()
        # Let the intended initial overwrite the filters:
        return {**changelist_filters, **initial}

    def _response_post_save(self, request: HttpRequest, obj: Model) -> HttpResponseRedirect:
        """
        Restore query parameters dropped by add_preserved_filters.

        ``_response_post_save`` is django's helper method that returns the user
        back to the changelist (or index if no perms) after a save.
        In its original form, the method uses
        ``django.contrib.admin.templatetags.admin_urls.add_preserved_filters``
        to tack on the changelist filters to the redirect url.
        (add_preserved_filters is also used to modify the links of result items)

        However, ``add_preserved_filters`` drops multiple values from a
        SelectMultiple by calling dict() on a parsed query string with multiple
        values:
        given the query string '?_changelist_filters=genre%3D176%26genre%3D594',
        ``add_preserved_filters`` will return '?genre=176', when it should be
        '?genre=176&genre=594'

        To preserve all the filters, we must restore these dropped values to
        the query string.
        """
        # Get the '_changelist_filters' part of the querystring.
        preserved_filters = self.get_preserved_filters(request)  # type: ignore[attr-defined]
        preserved_filters = dict(parse_qsl(preserved_filters))
        response = super()._response_post_save(request, obj)  # type: ignore[misc]
        if (not isinstance(response, HttpResponseRedirect)
                or not self.has_view_or_change_permission(request)  # type: ignore[attr-defined]
                or '_changelist_filters' not in preserved_filters):
            # Either the response is not a redirect (we need the url attribute) or
            # it redirects back to the index due to missing perms or
            # no changelist filters were preserved.
            return response
        # Extract the query params for the search form from the redirect url.
        post_url = response.url
        parsed_url = urlparse(post_url)
        post_url_query = QueryDict(parsed_url.query, mutable=True)
        # Create a QueryDict mapping of: search_form fields to
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

    def check(self, **kwargs: Any) -> List[checks.CheckMessage]:
        errors = super().check(**kwargs)  # type: ignore[misc]
        errors.extend(self._check_search_form_fields(**kwargs))
        return errors

    def _check_search_form_fields(self, **kwargs: Any) -> List[checks.CheckMessage]:
        """Check the fields given in self.search_form_kwargs."""
        if not self.has_search_form():
            return []
        errors = []
        # Relation fields defined by the model should be in the search form:
        rel_fields = [
            field.name
            for field in utils.get_model_fields(
                self.model, base=False, foreign=True, m2m=True  # type: ignore[attr-defined]
            )
        ]
        for field_path in self.search_form_kwargs.get('fields', []):
            msg = "Ignored search form field: '{field}'. %s".format(field=field_path)
            try:
                search_utils.get_dbfield_from_path(
                    self.model, field_path  # type: ignore[attr-defined]
                )
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
                    "\n\t%s" % rel_fields,
                    obj=self
                )
            )
        return errors


class MIZAdminSearchFormMixin(AdminSearchFormMixin):
    """Default mixin for MIZAdmin admin models adding more search options."""

    def get_search_form_class(self, **kwargs: Any) -> Type[SearchForm]:
        # Set the default form class for searchform_factory, unless a class is
        # provided by kwargs or search_form_kwargs:
        if not (
                'form' in kwargs or
                (self.search_form_kwargs and 'form' in self.search_form_kwargs)
        ):
            kwargs['form'] = MIZAdminSearchForm
        return super().get_search_form_class(**kwargs)

    def check(self, **kwargs: Any) -> List[checks.CheckMessage]:
        errors = super().check(**kwargs)  # type: ignore[misc]
        errors.extend(self._check_tabular_autocompletes(**kwargs))
        return errors

    def _check_tabular_autocompletes(self, **_kwargs: Any) -> List[checks.CheckMessage]:
        """
        Check that tabular autocomplete fields of inlines also have tabular
        autocomplete widgets in the search form.
        """
        if not self.has_search_form():  # pragma: no cover
            return []

        search_form_tabulars = self.search_form_kwargs.get('tabular', [])
        messages = []
        # noinspection PyUnresolvedReferences
        for inline_cls in self.inlines:  # type: ignore[attr-defined]
            for field_name in getattr(inline_cls, 'tabular_autocomplete', []):
                if field_name not in self.search_form_kwargs['fields']:
                    continue
                if field_name not in search_form_tabulars:
                    messages.append(
                        checks.Info(
                            f"Inline tabular {field_name!r} of inline {inline_cls!r} has no "
                            f"corresponding tabular on the changelist search form.",
                            obj=self,
                            hint=f"Add {field_name!r} to search_form_kwargs['tabular']",
                        )
                    )
        return messages


# noinspection PyUnresolvedReferences
class ChangelistSearchFormMixin(object):
    """Mixin for changelist classes to incorporate the new search form."""

    def __init__(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        # Preserve the contents of request.GET.
        # The changelist attribute 'param' is insufficient as it destroys
        # the multiple values of a MultiValueDict by calling items() instead
        # of lists(): self.params = dict(request.GET.items())
        # django's changelist does not inherit the base View class that sets
        # self.request during setup().
        self.request = request
        super().__init__(request, *args, **kwargs)  # type: ignore[call-arg]

    def get_filters_params(self, params: Optional[dict] = None) -> dict:
        """Replace the default filter params with those from the search form."""
        filter_params: dict = super().get_filters_params(params)  # type: ignore[misc]
        if not isinstance(self.model_admin, AdminSearchFormMixin):  # type: ignore[attr-defined]
            return filter_params
        # If the ModelAdmin instance has a search form, let the form come up
        # with filter parameters.
        # Should the request contain query parameters that a part of the search
        # form, prioritize params returned by the form over the params included
        # in the request.
        search_form_params = self.model_admin.get_search_form(  # type: ignore[attr-defined]
            data=self.request.GET
        ).get_filters_params()
        if search_form_params:
            return search_form_params
        return filter_params
