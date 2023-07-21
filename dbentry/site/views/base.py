"""
Base views for the other views of the site app.
"""

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.http import JsonResponse
from django.urls import reverse, NoReverseMatch
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.views.generic import UpdateView, ListView
from django.views.generic.base import ContextMixin
from formset.views import FormViewMixin

from dbentry.search.forms import MIZSelectSearchFormFactory
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


class BaseViewMixin(ContextMixin):
    """Mixin for all views of the `miz_site` site."""

    title = ""
    site = miz_site

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"title": self.title, "wiki_url": settings.WIKI_URL, "model_list": self.site.model_list})
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
        ctx.update({"model": self.model, "opts": self.model._meta})
        return ctx


class BaseModelView(PermissionRequiredMixin, ModelViewMixin, FormViewMixin, UpdateView):
    inlines: list["InlineModel"] = ()

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
        self.add = self.extra_context["add"] is True

    def get_permission_required(self):
        action = "add" if self.add else "change"
        return [perms.get_perm(action, self.opts)]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        title_suffix = "hinzufügen" if self.add else "ändern"
        ctx["title"] = f"{capfirst(self.opts.verbose_name)} {title_suffix}"
        return ctx

    def get_object(self, queryset=None):
        if self.extra_context["add"] is False:
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
            if extra_data.get("add_another"):
                if self.add:
                    # Already on the 'add' page.
                    return self.request.path
                else:
                    return reverse(urlname("add", self.opts))
            elif extra_data.get("continue"):
                # NOTE: with django-formset submit buttons, redirecting should not be needed if
                # we are already on the change page?
                return reverse(urlname("change", self.opts), args=[self.object.pk])
        return reverse(urlname("changelist", self.opts))

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

        return JsonResponse({"success_url": self.get_success_url()})


class BaseListView(ModelViewMixin, ListView):
    """
    Base view for displaying a list of model objects ("changelist").

    Set attribute `list_display` to control which fields are displayed on the
    changelist.

    Additional attributes:
        - order_unfiltered_results (bool): if True, apply ordering to unfiltered
          changelist querysets. Setting this to False will only apply 'id'
          ordering to an unfiltered queryset. This is useful for speeding up
          the initial request for a changelist.
        - prioritize_search_ordering (bool): if True, do not override the
          ordering set by queryset.search()
    """

    template_name = "mizdb/changelist.html"
    list_display = ()
    list_display_links = ()
    sortable_by = None
    paginate_by = 100
    empty_value_display = "-"
    page_kwarg = PAGE_VAR

    order_unfiltered_results = True
    prioritize_search_ordering = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookup_opts = self.opts = self.model._meta  # TODO: probably not needed anymore?
        if self.list_display:
            self.sortable_by = self.list_display  # TODO: what does this do? Is sortable_by needed at all?
        self.formset = None  # required by tag admin_list.result_hidden_fields  # TODO: is this still needed?

    def get_ordering_field(self, field_name):
        """
        Return the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method on the view with the
        'order_field' attribute.

        Return None if no proper model field name can be matched.
        """
        # NOTE: not used since custom ordering on a changelist is not yet implemented
        try:
            field = self.opts.get_field(field_name)
            return field.name
        except FieldDoesNotExist:
            # See whether field_name is a name of a non-field
            # that allows sorting.
            if hasattr(self, field_name):
                attr = getattr(self, field_name)
                return getattr(attr, "ordering", None)

    def get_query_string(self, new_params=None, remove=None):
        # Used by template tag paginator_url
        if new_params is None:
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
        queryset = self.get_search_results(super().get_queryset())
        return self.order_queryset(queryset)

    @property
    def search_term(self):
        return self.request.GET.get(SEARCH_VAR, "")

    def get_search_results(self, queryset):
        if self.search_term:
            return queryset.search(self.search_term, ranked=ORDER_VAR not in self.request.GET)
        return queryset

    def _get_default_ordering(self):
        if self.ordering is not None:
            return self.ordering
        elif self.opts.ordering:
            return self.opts.ordering
        else:
            return []

    def get_ordering_fields(self, queryset):
        """Return the list of ordering fields for the results queryset."""
        # TODO: add order params from request query string
        if self.prioritize_search_ordering and self.search_term:
            # queryset.search has applied its own ordering, do not override:
            return queryset.query.order_by
        else:
            ordering = [*self._get_default_ordering()]
            ordering.extend(queryset.query.order_by)
            ordering.append("id")
            return ordering

    def order_queryset(self, queryset):
        if not (queryset.query.has_filters() or self.order_unfiltered_results):
            # Do not apply (expensive) ordering on an unfiltered queryset.
            return queryset.order_by("id")
        return queryset.order_by(*self.get_ordering_fields(queryset))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        paginator = ctx["paginator"]
        ctx.update(
            {
                # some template tags require this view object:
                "cl": self,
                # call list on the pagination page range generator, because it will
                # be consumed more than once:
                "page_range": list(paginator.get_elided_page_range(ctx["page_obj"].number)),
                "pagination_required": paginator.count > 100,
                "result_rows": self.get_result_rows(ctx["object_list"]),
                "result_headers": self.get_result_headers(),
                "result_count": self.object_list.count(),
                "total_count": self.model.objects.count(),
                "search_term": self.request.GET.get(SEARCH_VAR, ""),
            }
        )
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
        attr = getattr(self, name, None)
        if attr is not None and hasattr(attr, "description"):
            # This is a view (display) callable with a description attribute.
            return attr, attr.description
        try:
            attr = self.opts.get_field(name)
        except FieldDoesNotExist:
            # This is not a model field either!
            label = name
        else:
            if attr.verbose_name[0].isupper():
                # This is probably a verbose name set by the user and not just
                # the default which starts with a lower letter.
                return attr, attr.verbose_name
            label = name
        return attr, label.replace("_", " ").capitalize()

    def get_result_headers(self):
        """Return the headers for the result list table."""
        # TODO: add header links for sorting like in the django admin changelist
        headers = []
        for name in self.list_display or ["__str__"]:
            if name == "__str__":
                headers.append({"text": self.model._meta.verbose_name})
            else:
                _attr, label = self._lookup_field(name)
                headers.append({"text": label})
        return headers

    def add_list_display_annotations(self, queryset):
        """Add annotations for list_display items to the given queryset."""
        if hasattr(queryset, "overview"):
            return queryset.overview()
        return queryset

    def get_result_rows(self, object_list):
        """Return the result rows for the given object list."""
        return [self.get_result_row(r) for r in self.add_list_display_annotations(object_list)]

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
        for name in self.list_display or ["__str__"]:
            if name == "__str__":
                value = str(result)
            else:
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
                    if getattr(attr, "flatchoices", None):  # pragma: no cover
                        # Use the human-readable part of the choice:
                        value = dict(attr.flatchoices).get(value, "")
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


class SearchableListView(SearchFormMixin, BaseListView):
    """
    A BaseListView with a search form.

    Configure the search form via the attribute `search_form_kwargs`.
    """

    searchform_factory = MIZSelectSearchFormFactory()

    def get_search_results(self, queryset):
        queryset = super().get_search_results(queryset)
        search_form = self.get_search_form(data=self.request.GET)
        if search_form.is_valid():
            filter_params = self.get_filters(search_form)
            queryset = queryset.filter(**self.get_filters(search_form))
        return queryset

    def get_filters(self, search_form):
        filters = {}
        for key, value in search_form.get_filters_params().items():
            if key.endswith("__in"):
                value = value.split(",")
            elif key.endswith("__isnull"):
                value = value.lower() not in ("", "false", "0")
            filters[key] = value
        return filters
