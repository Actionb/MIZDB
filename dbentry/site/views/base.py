"""
Base views for the other views of the site app.
"""
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.text import capfirst
from django.views.generic import UpdateView
from django.views.generic.base import ContextMixin
from formset.views import IncompleteSelectResponseMixin, FormViewMixin
from formset.widgets import DualSelector, Selectize

from dbentry.fts.query import TextSearchQuerySetMixin
from dbentry.site.registry import miz_site
from dbentry.utils import permission as perms


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_namespace = settings.SITE_NAMESPACE

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
                return self.request.path
            elif extra_data.get('continue'):
                return reverse(
                    f'{self.url_namespace}:{self.opts.app_label}_{self.opts.model_name}_change',
                    args=[self.object.pk]
                )
        return reverse(
            f"{self.url_namespace}:{self.opts.app_label}_{self.opts.model_name}_changelist"
        )

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
