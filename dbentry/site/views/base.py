"""
Base views for the other views of the site app.
"""
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse, NoReverseMatch
from django.utils.encoding import force_str
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.views.generic import UpdateView, ListView
from django.views.generic.base import ContextMixin
from formset.renderers.bootstrap import FormRenderer
from formset.views import IncompleteSelectResponseMixin, FormViewMixin
from formset.widgets import DualSelector, Selectize

from dbentry.fts.query import TextSearchQuerySetMixin
from dbentry.search.forms import SearchForm
from dbentry.search.mixins import SearchFormMixin
from dbentry.site.registry import miz_site
from dbentry.utils import permission as perms
from dbentry.utils.html import create_hyperlink
from dbentry.utils.permission import has_view_permission
from dbentry.utils.url import get_change_url, urlname

# Constants for the changelist views
ALL_VAR = "all"
ORDER_VAR = "o"
PAGE_VAR = "p"
SEARCH_VAR = "q"


class AutocompleteMixin(IncompleteSelectResponseMixin, FormViewMixin):
    """
    Endpoint for the autocomplete/incomplete requests of django-formset.

    If a request is made against a model that can provide text search, the
    autocomplete results will be from such a text search query.

    A model counts as able to 'provide text search' if it inherits from
    dbentry.fts.query.TextSearchQuerySetMixin.
    """

    def get(self, request, **kwargs):
        if request.accepts('application/json') and 'field' in request.GET:
            try:
                self.get_field(request.GET['field'])
            except KeyError:
                return HttpResponseBadRequest(f"No such field: {request.GET['field']}")

            if self.can_do_text_search(request):
                return self._fetch_text_search_options(request)
        return super().get(request, **kwargs)

    def can_do_text_search(self, request):
        """
        Return whether a full text search should be attempted.

        Return True if there is a search term and the queryset supports text
        search.
        """
        return (
                request.GET.get('search')
                and isinstance(self.get_autocomplete_queryset(request), TextSearchQuerySetMixin)
        )

    def get_autocomplete_queryset(self, request):
        """Return the queryset of the targeted autocomplete field."""
        field = self.get_field(request.GET['field'])
        assert isinstance(field.widget, (Selectize, DualSelector))
        return field.widget.choices.queryset

    def _fetch_text_search_options(self, request):
        field = self.get_field(request.GET['field'])
        widget = field.widget
        queryset = self.get_autocomplete_queryset(request)

        data = {'total_count': queryset.count()}

        try:
            offset = int(request.GET.get('offset'))
        except TypeError:
            offset = 0

        if widget.filter_by and any(k.startswith('filter-') for k in request.GET.keys()):
            filters = {key: request.GET.getlist(f'filter-{key}') for key in widget.filter_by.keys()}
            data['filters'] = filters
            queryset = queryset.filter(widget.build_filter_query(filters))

        if search := request.GET.get('search'):
            data['search'] = search
            queryset = queryset.search(unquote(search))
            incomplete = None  # incomplete state unknown
        else:
            incomplete = queryset.count() - offset > widget.max_prefetch_choices

        limited_qs = queryset[offset:offset + widget.max_prefetch_choices]
        to_field_name = field.to_field_name if field.to_field_name else 'pk'
        if widget.group_field_name:
            options = [{
                'id': getattr(item, to_field_name),
                'label': str(item),
                'optgroup': force_str(getattr(item, widget.group_field_name)),
            } for item in limited_qs]
        else:
            options = [{
                'id': getattr(item, to_field_name),
                'label': str(item),
            } for item in limited_qs]
        data.update(
            count=len(options),
            incomplete=incomplete,
            options=options,
        )
        return JsonResponse(data)


class BaseViewMixin(ContextMixin):
    """Mixin for all views of the `miz_site` site."""

    title = ""
    site = miz_site

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'title': self.title,
            'wiki_url': settings.WIKI_URL,
            'model_list': self.site.model_list,
        })
        return ctx


class ModelViewMixin(BaseViewMixin):
    """Mixin for views that interact with a model."""

    model = None
    opts = None
    pk_url_kwarg = "object_id"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opts = self.model._meta

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'model': self.model,
            'opts': self.model._meta,
        })
        return ctx


class BaseModelView(PermissionRequiredMixin, ModelViewMixin, AutocompleteMixin, UpdateView):
    inlines: list['InlineModel'] = ()

    def has_permission(self):
        return perms.has_view_permission(self.request.user, self.opts)

    ###########################################################################
    #                                   Inlines
    ###########################################################################

    # def get_inline_instances(self, request, obj=None):
    #     inline_instances = []
    #     for inline_class in self.inlines:
    #         inline = inline_class(self.model, site)
    #         if request:
    #             if not (
    #                     inline.has_view_or_change_permission(request, obj)
    #                     or inline.has_add_permission(request, obj)
    #                     or inline.has_delete_permission(request, obj)
    #             ):
    #                 continue
    #             if not inline.has_add_permission(request, obj):
    #                 inline.max_num = 0
    #         inline_instances.append(inline)
    #
    #     return inline_instances
    #
    # def get_formsets_with_inlines(self, request, obj=None):
    #     """
    #     Yield formsets and the corresponding inlines.
    #     """
    #     for inline in self.get_inline_instances(request, obj):
    #         yield inline.get_formset(request, obj), inline
    #
    # def get_formset_kwargs(self, request, obj, inline, prefix):
    #     formset_params = {
    #         "instance": obj,
    #         "prefix": prefix,
    #         "queryset": inline.get_queryset(request),
    #     }
    #     if request.method == "POST":
    #         formset_params.update(
    #             {
    #                 "data": request.POST.copy(),
    #                 "files": request.FILES,
    #                 "save_as_new": "_saveasnew" in request.POST,
    #             }
    #         )
    #     return formset_params
    #
    # def _create_formsets(self, request, obj, change):
    #     """Helper function to generate formsets for add/change_view."""
    #     formsets = []
    #     inline_instances = []
    #     prefixes = {}
    #     get_formsets_args = [request]
    #     if change:
    #         get_formsets_args.append(obj)
    #     for FormSet, inline in self.get_formsets_with_inlines(*get_formsets_args):
    #         prefix = FormSet.get_default_prefix()
    #         prefixes[prefix] = prefixes.get(prefix, 0) + 1
    #         if prefixes[prefix] != 1 or not prefix:
    #             prefix = "%s-%s" % (prefix, prefixes[prefix])
    #         formset_params = self.get_formset_kwargs(request, obj, inline, prefix)
    #         formset = FormSet(**formset_params)
    #
    #         def user_deleted_form(request, obj, formset, index):
    #             """Return whether the user deleted the form."""
    #             return (
    #                     inline.has_delete_permission(request, obj)
    #                     and "{}-{}-DELETE".format(formset.prefix, index) in request.POST
    #             )
    #
    #         # Bypass validation of each view-only inline form (since the form's
    #         # data won't be in request.POST), unless the form was deleted.
    #         if not inline.has_change_permission(request, obj if change else None):
    #             for index, form in enumerate(formset.initial_forms):
    #                 if user_deleted_form(request, obj, formset, index):
    #                     continue
    #                 form._errors = {}
    #                 form.cleaned_data = form.initial
    #         formsets.append(formset)
    #         inline_instances.append(inline)
    #     return formsets, inline_instances


class BaseEditView(BaseModelView, UpdateView):
    """Base class for 'add' or 'change' views."""

    template_name = "mizdb/change_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add = self.extra_context['add'] is True

    def get_permission_required(self):
        action = 'add' if self.add else 'change'
        return [perms.get_perm(action, self.opts)]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        title_suffix = 'hinzufügen' if self.add else 'ändern'
        ctx['title'] = f"{capfirst(self.opts.verbose_name)} {title_suffix}"
        return ctx

    def get_object(self, queryset=None):
        if self.extra_context['add'] is False:
            return super().get_object(queryset)

    def get_success_url(self):
        """
        Return the success_url that corresponds with the submit button that was
        pressed.

        The submit buttons add a little 'extra_data' to the request:
          - 'add_another' -> return the same view with an empty form
          - 'continue' -> show the change form of the current object
          - 'add' -> return to the changelist (default)
        """
        if extra_data := self.get_extra_data():
            if extra_data.get('add_another'):
                if self.add:
                    # Already on the 'add' page.
                    return self.request.path
                else:
                    return reverse(urlname('add', self.opts))
            elif extra_data.get('continue'):
                # NOTE: with django-formset submit buttons, redirecting should not be needed if
                # we are already on the change page?
                return reverse(urlname('change', self.opts), args=[self.object.pk])
        return reverse(urlname('changelist', self.opts))

    def form_valid(self, form):
        # Do not save the form instance until the formsets have been validated.
        self.object = form.save(commit=False)
        formsets = ()
        if all([formset.is_valid() for formset in formsets]):
            # NOTE: Can't we just do this?:
            # form.save()
            self.object.save()
            form.save_m2m()
            for formset in formsets:
                formset.save()
        else:
            # TODO: don't we need to add the formset errors to the context?
            return self.form_invalid(form)

        return JsonResponse({'success_url': self.get_success_url()})


class BaseListView(ModelViewMixin, ListView):
    """
    Base view for displaying a list of model objects ("changelist").

    Set attribute `list_display` to control which fields are displayed on the
    changelist.
    """
    template_name = "mizdb/changelist.html"
    list_display = ()
    list_display_links = ()
    sortable_by = None
    paginate_by = 100
    empty_value_display = "-"
    page_kwarg = PAGE_VAR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookup_opts = self.opts = self.model._meta  # TODO: probably not needed anymore?
        if self.list_display:
            self.sortable_by = self.list_display  # TODO: what does this do? Is sortable_by needed at all?
        self.formset = None  # required by tag admin_list.result_hidden_fields  # TODO: is this still needed?

    def _get_default_ordering(self):
        # NOTE: not (yet?) used
        ordering = []
        if self.ordering:
            ordering = self.ordering
        elif self.opts.ordering:
            ordering = self.opts.ordering
        return ordering

    def get_ordering_field(self, field_name):
        """
        Return the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method on the view with the
        'order_field' attribute.

        Return None if no proper model field name can be matched.
        """
        # NOTE: not (yet?) used
        try:
            field = self.opts.get_field(field_name)
            return field.name
        except FieldDoesNotExist:
            # See whether field_name is a name of a non-field
            # that allows sorting.
            if hasattr(self, field_name):
                attr = getattr(self, field_name)
                return getattr(attr, "order_field", None)

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None:  # pragma: no cover
            new_params = {}
        if remove is None:
            remove = []
        p = dict(self.request.GET.items()).copy()
        for r in remove:
            for k in list(p):
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return "?%s" % urlencode(sorted(p.items()))

    def get_queryset(self):
        queryset = super().get_queryset()
        if q := self.request.GET.get(SEARCH_VAR):
            queryset = self.get_search_results(queryset, q)
        if not hasattr(queryset, "overview"):
            return queryset
        return queryset.overview()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        paginator = ctx["paginator"]
        ctx.update({
            # some template tags require this view object:
            "cl": self,
            # call list on the pagination page range generator, because it will
            # be consumed more than once:
            "page_range": list(paginator.get_elided_page_range(ctx["page_obj"].number)),
            "pagination_required": paginator.count > 100,
            "result_rows": [self.get_result_row(r) for r in ctx["object_list"]],
            "result_headers": self.get_result_headers(),
            "result_count": self.object_list.count(),
            "total_count": self.model.objects.count(),
            "search_term": self.request.GET.get(SEARCH_VAR, ''),
        })
        return ctx

    def get_empty_value_display(self):
        """
        Return the empty_value_display set on this view.
        """
        return mark_safe(self.empty_value_display)

    def _lookup_field(self, name):
        """
        Get the model field or view callable for the given name, and return it
        and an appropriate label.
        """
        attr = None
        if hasattr(self, name):
            attr = getattr(self, name)
            if hasattr(attr, "short_description"):
                label = attr.short_description
            else:
                label = name
        else:
            try:
                attr = self.opts.get_field(name)
                label = attr.verbose_name
            except FieldDoesNotExist:
                # This is not a view callable or a model field:
                label = name
        return attr, label.replace("_", " ").capitalize()

    def get_result_headers(self):
        """Return the headers for the result list table."""
        # TODO: add header links for sorting like in the django admin changelist
        headers = []
        for name in self.list_display:
            _attr, label = self._lookup_field(name)
            headers.append({"text": label.replace("_", " ").capitalize()})
        return headers

    def get_result_row(self, result):
        """Return the values to display in the row for the given result."""

        def link_in_col(is_first, field_name):
            if self.list_display_links is None:
                return False
            if is_first and not self.list_display_links:
                return True
            return field_name in self.list_display_links

        result_items = []
        first = True
        for name in self.list_display:
            attr, _label = self._lookup_field(name)
            if callable(attr):
                value = attr(result)
            else:
                # Assume that this is a model field.
                if isinstance(attr, models.ForeignKey):
                    value = getattr(result, attr.name)
                    if value is not None:
                        value = str(value)
                else:
                    value = getattr(result, attr.attname)
                if getattr(attr, 'flatchoices', None):
                    # Use the human-readable part of the choice:
                    value = dict(attr.flatchoices).get(value, '')
            if not value:
                value = self.get_empty_value_display()
            if link_in_col(first, name) and has_view_permission(self.request.user, self.opts):
                # TODO: add preserved filters to links
                try:
                    url = get_change_url(self.request, result)
                except NoReverseMatch:
                    pass
                else:
                    value = create_hyperlink(url, value)
            result_items.append(value)
            first = False
        return result_items

    def get_search_results(self, queryset, search_term):
        return queryset.search(search_term, ranked=ORDER_VAR not in self.request.GET)


class ChangelistSearchForm(SearchForm):
    default_renderer = FormRenderer(
        label_css_classes=("col-lg-1", "col-form-label"),
        control_css_classes=("col-lg-10", "col-xl-9", "col-xxl-8"),
        field_css_classes={'*': 'row mb-2'},
        form_css_classes=("ps-2",),
    )


class SearchableListView(SearchFormMixin, AutocompleteMixin, BaseListView):
    """A BaseListView with a search form."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.form_class = self.get_search_form_class()  # django-formset requires this

    def get_search_form_class(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = ChangelistSearchForm
        return super().get_search_form_class(**kwargs)
