from collections import OrderedDict
from typing import Any, Dict, List, OrderedDict as OrderedDictType, Sequence, Tuple, Type, Union

from django import views
from django.apps import apps
from django.contrib.admin.utils import get_fields_from_path
from django.contrib.auth import get_permission_codename
from django.db.models import (
    Count, F, ManyToManyRel, ManyToOneRel, Model, OneToOneRel, Q, QuerySet,
    Window
)
from django.db.models.query import RawQuerySet
from django.forms import Form
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import SafeString, SafeText

from dbentry.base.views import MIZAdminMixin, SuperUserOnlyMixin
from dbentry.tools.decorators import register_tool
from dbentry.tools.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm, UnusedObjectsForm
)
from dbentry.utils.html import get_obj_link, create_hyperlink
from dbentry.utils.models import get_model_from_string, get_model_relations
from dbentry.utils.url import get_changelist_url
from dbentry.utils.query import string_list

Relations = Union[ManyToManyRel, ManyToOneRel, OneToOneRel]

# TODO: must make SiteSearchView available for both site and admin app (URL namespace)


def find_duplicates(queryset: QuerySet, fields: Sequence[str]) -> RawQuerySet:
    """
    Find records in the queryset that share values in the specified fields.

    Returns a raw queryset containing the duplicate instances.
    """
    window_expression = Window(
        expression=Count('*'),
        partition_by=fields,
        order_by=[F(field).desc() for field in fields]
    )
    counts_query = queryset.annotate(c=window_expression).values('pk', 'c')
    # Need to filter out rows without duplicates, but Window expressions are
    # not allowed in the filter clause - so use this workaround:
    # https://code.djangoproject.com/ticket/28333#comment:20
    sql, params = counts_query.query.sql_with_params()
    return queryset.raw(f"SELECT * FROM ({sql}) counts WHERE counts.c > 1", params)


class ModelSelectView(views.generic.FormView):
    """
    A FormView that redirects to another view with the model chosen in the form
    as initkwargs.

    Attributes:
        - ``next_view`` (str): view name of the next view. reverse() must be
          able to return a URL using this view name.
    """

    template_name = 'admin/basic_form.html'
    form_class = ModelSelectForm

    form_method: str = 'get'
    submit_value: str = 'Weiter'
    submit_name: str = 'submit'
    next_view: str = 'admin:index'

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        # Add context variables specific to admin/basic_form.html:
        context['submit_value'] = self.submit_value
        context['submit_name'] = self.submit_name
        context['form_method'] = self.form_method
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.submit_name in request.GET:
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse(self.next_view, kwargs=self.get_next_view_kwargs())

    def get_next_view_kwargs(self) -> Dict[str, dict]:
        return {'model_name': self.request.GET.get('model_select')}


@register_tool(
    url_name='tools:dupes_select',
    index_label='Duplikate finden',
    superuser_only=True
)
class DuplicateModelSelectView(MIZAdminMixin, SuperUserOnlyMixin, ModelSelectView):
    """
    Main entry point for the duplicates search.

    It lets the user choose a model to search for duplicates in and then
    redirects to the DuplicateObjectsView.
    """

    title = 'Duplikate finden'
    next_view = 'dupes'
    form_class = ModelSelectForm


class DuplicateObjectsView(MIZAdminMixin, views.generic.FormView):
    """
    A FormView that finds, displays and, if so requested, merges duplicates.

    The view's form contains the model fields with which a search for duplicates
    is done. Duplicates are model instances that have the same values in the
    model fields selected in the form.
    These duplicates are grouped together according to these equivalent values
    and the possibility for merging each group is provided.
    """

    template_name = 'tools/dupes.html'
    form_class = DuplicateFieldsSelectForm

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        if not kwargs.get('model_name'):
            raise TypeError("Model not provided.")
        # noinspection PyAttributeOutsideInit
        self.model = get_model_from_string(kwargs['model_name'], app_label='dbentry')

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle the request to find duplicates."""
        form = self.get_form()
        context = self.get_context_data(form=form, **kwargs)
        if 'get_duplicates' in request.GET and form.is_valid():
            # Use the human-readable part of the selected choices for the
            # headers of the listing table:
            choices = dict(form.fields['display'].choices)
            context['headers'] = [choices[selected] for selected in form.cleaned_data['display']]
            # Calculate the (percentile) width of the headers; 25% of the width
            # is already taken up by the three headers 'merge','id','link'.
            context['headers_width'] = str(int(80 / len(context['headers'])))
            context['items'] = self.build_duplicates_items(form)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        # noinspection PyUnresolvedReferences
        context['title'] = 'Duplikate: ' + self.model._meta.verbose_name
        # noinspection PyUnresolvedReferences
        context['breadcrumbs_title'] = self.model._meta.verbose_name
        return context

    def get_form_kwargs(self) -> dict:
        """Return the kwargs for the fields select form."""
        kwargs = super().get_form_kwargs()
        kwargs['model'] = self.model
        kwargs['data'] = self.request.GET
        return kwargs

    def build_duplicates_items(self, form: Form) -> list:
        """
        Prepare the content of the table that lists the duplicates.

        Returns a list of 2-tuples. The first item of that 2-tuple contains
        table date for the duplicate instances. The second item is a link to the
        changelist of those instances. Example:
        [
            (
                [(model instance, change page URL, display values), ...],
                <link to the changelist of the duplicate instances>
            ), ...
        ]
        """
        # Optimize the query by using StringAgg on values for many_to_many and
        # many_to_one relations. Use select_related for many_to_one relations.
        annotations = {}
        select_related = []
        display_fields = []
        for path in form.cleaned_data['display']:
            fields = get_fields_from_path(self.model, path)
            if not fields[0].is_relation:
                display_fields.append(path)
                continue
            if len(fields) == 1:
                # path is the name of a many_to_one (ForeignKey) relation field
                # declared on this model.
                select_related.append(path)
            else:
                # A many_to_many or many_to_one relation.
                annotations[path] = string_list(path)
            display_fields.append(path)

        # noinspection PyUnresolvedReferences
        search_fields = form.cleaned_data['select']
        # noinspection PyUnresolvedReferences
        queryset = self.model.objects.all()
        duplicates = (
            queryset.filter(pk__in=[o.pk for o in find_duplicates(queryset, search_fields)])
            .select_related(*select_related)
            .annotate(**annotations)
            .order_by(*search_fields, 'pk')
        )

        # noinspection PyShadowingNames
        def make_dupe_item(obj: Model) -> Tuple[Model, SafeString, list[str]]:
            """
            Provide a tuple to add to a group of duplicates.

            The tuple consists of the duplicate model instance, a link to its
            change page and the instance's values for the overview display.
            """
            values = []
            for f in display_fields:
                v = ''
                if getattr(obj, f) is not None:
                    v = str(getattr(obj, f))
                    if len(v) > 100:
                        v = v[:100] + ' [...]'
                values.append(v)
            link = get_obj_link(self.request, obj, namespace="admin", blank=True)
            return obj, link, values

        # noinspection PyShadowingNames
        def get_cl_link(dupe_group: List[Tuple[Model, SafeString, list[str]]]) -> SafeString:
            """Provide a link to the changelist page for this group of duplicate items."""
            cl_url = get_changelist_url(
                self.request,
                self.model,
                obj_list=[item[0] for item in dupe_group],
                namespace='admin'
            )
            return create_hyperlink(
                url=cl_url, content='Änderungsliste',
                # 'class' cannot be a keyword argument, so wrap the element
                # attribute arguments in a dictionary.
                **{'target': '_blank', 'class': 'button', 'style': 'padding: 10px 15px;'}
            )

        groups: list = []
        # A group of duplicates and the data that makes them duplicates of each
        # other.
        dupe_group = dupe_data = None
        for i, obj in enumerate(duplicates):
            if {f: getattr(obj, f) for f in search_fields} == dupe_data and dupe_group is not None:
                dupe_group.append(make_dupe_item(obj))
                if i == duplicates.count() - 1:
                    # This is the last item in the queryset: append the group.
                    groups.append((dupe_group, get_cl_link(dupe_group)))
            else:
                # A new set of duplicates begins here.
                if dupe_group:
                    groups.append((dupe_group, get_cl_link(dupe_group)))
                dupe_data = {f: getattr(obj, f) for f in search_fields}
                dupe_group = [make_dupe_item(obj)]
        return groups


@register_tool(
    url_name='tools:find_unused',
    index_label='Unreferenzierte Datensätze',
    superuser_only=True
)
class UnusedObjectsView(MIZAdminMixin, SuperUserOnlyMixin, ModelSelectView):
    """
    View that enables finding objects of a given model that are referenced by
    reversed related models less than a given limit.
    """

    form_class = UnusedObjectsForm
    template_name = 'tools/find_unused.html'

    form_method = 'get'
    submit_name = 'get_unused'
    submit_value = 'Suchen'
    breadcrumbs_title = title = 'Unreferenzierte Datensätze'

    def get_form_kwargs(self) -> dict:
        """Use request.GET as form data instead of request.POST."""
        kwargs = super().get_form_kwargs()
        if self.submit_name in self.request.GET:
            # Only include data when the search button has been pressed to
            # suppress validation on the first visit on this page.
            kwargs['data'] = self.request.GET
        return kwargs

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle the request to find unused objects."""
        context = self.get_context_data(**kwargs)
        if self.submit_name in request.GET:
            form = self.get_form()
            if form.is_valid():
                model_name = form.cleaned_data['model_select']
                model = get_model_from_string(model_name)
                relations, queryset = self.get_queryset(model, form.cleaned_data['limit'])
                # noinspection PyUnresolvedReferences
                cl_url = get_changelist_url(request, model, obj_list=queryset, namespace='admin')
                context_kwargs = {
                    'form': form,
                    'items': self.build_items(relations, queryset),
                    'changelist_link': create_hyperlink(
                        url=cl_url, content='Änderungsliste',
                        **{'target': '_blank', 'class': 'button'}
                    )
                }
                context.update(**context_kwargs)
        return self.render_to_response(context)

    # noinspection PyMethodMayBeStatic
    def get_queryset(
            self, model: Type[Model], limit: int
    ) -> Tuple[OrderedDictType[Relations, dict], QuerySet]:
        """
        Prepare the queryset that includes all objects of ``model`` that have
        less than ``limit`` reverse related objects.

        Returns a 2-tuple:
            - a OrderedDict containing information for each reverse relation
            - queryset of the 'unused' objects
        """
        # noinspection PyUnresolvedReferences
        queryset = model.objects
        relations = OrderedDict()
        # all_ids is a 'screenshot' of all IDs of the model's objects.
        # Starting out, unused will also contain all IDs, but any ID that is
        # from an object that exceeds the limit will be removed.
        all_ids = unused = set(queryset.values_list('pk', flat=True))

        # For each reverse relation, query for the 'unused' objects, and remove
        # all OTHER IDs (i.e. those of objects that exceed the limit) from the
        # set 'unused'.
        for rel in get_model_relations(model, forward=False):
            if rel.model == rel.related_model:
                # self relation
                continue
            if rel.many_to_many:
                if rel.related_model == model:
                    # A m2m relation established by THIS model.
                    query_name = rel.field.name
                    related_model = rel.model
                else:
                    # A m2m relation established by the other model.
                    query_name = rel.name
                    related_model = rel.related_model
            else:
                # A reverse m2o relation.
                query_name = rel.name
                related_model = rel.related_model

            # For this relation, get objects that do not exceed the limit.
            qs = queryset.order_by().annotate(c=Count(query_name)).filter(Q(c__lte=limit))
            counts = {pk: c for pk, c in qs.values_list('pk', 'c')}
            # Remove the ids of the objects that exceed the limit for this relation.
            unused.difference_update(all_ids.difference(counts))
            relations[rel] = {
                'related_model': related_model,
                'counts': counts
            }
        return relations, queryset.filter(pk__in=unused)

    def build_items(
            self,
            relations: OrderedDictType[Relations, dict],
            queryset: QuerySet
    ) -> List[Tuple[SafeText, str]]:
        """Build items for the context."""
        items = []
        under_limit_template = '{model_name} ({count!s})'
        for obj in queryset:
            under_limit = []
            for info in relations.values():
                count = info['counts'].get(obj.pk, 0)
                under_limit.append(
                    under_limit_template.format(
                        model_name=info['related_model']._meta.verbose_name,
                        count=count
                    )
                )
            items.append(
                (
                    get_obj_link(self.request, obj, namespace="admin", blank=True),
                    ", ".join(sorted(under_limit))
                )
            )
        return items


class SiteSearchView(views.generic.TemplateView):
    """
    A view enabling looking up a search term on every model installed on a
    given app.
    """

    app_label = ''
    template_name = 'tools/site_search.html'

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        q = request.GET.get('q', '')
        if q:
            context['q'] = q
            context['results'] = self.get_result_list(q)
        return self.render_to_response(context)

    def _get_models(self, app_label: str = '') -> List[Model]:
        """
        Return a list of models to be queried.

        The user must have 'view' or 'change' permission for a model to be
        included in the list.

        Args:
            app_label (str): name of the app whose models should be queried
        """

        def has_permission(user, model):
            opts = model._meta
            codename_view = get_permission_codename('view', opts)
            codename_change = get_permission_codename('change', opts)
            return (
                    user.has_perm('%s.%s' % (opts.app_label, codename_view))
                    or user.has_perm('%s.%s' % (opts.app_label, codename_change))
            )

        app = apps.get_app_config(app_label or self.app_label)
        return [
            model for model in app.get_models()
            if has_permission(self.request.user, model)
        ]

    def _search(self, model: Model, q: str) -> Any:
        """Search the given model for the search term ``q``."""
        raise NotImplementedError("The view class must implement the search.")  # pragma: no cover

    def get_result_list(self, q: str) -> List[SafeText]:
        """
        Perform the queries for the search term ``q``.

        Returns:
            a list of hyperlinks to the changelists containing the results,
             sorted by the model's object name
        """
        results = []
        for model in sorted(self._get_models(), key=lambda m: m._meta.object_name):
            model_results = self._search(model, q)
            if not model_results:
                continue
            # noinspection PyUnresolvedReferences
            label = "%s (%s)" % (model._meta.verbose_name_plural, len(model_results))
            url = get_changelist_url(self.request, model, namespace='admin')
            if url:
                url += f"?q={q!s}"
                results.append(create_hyperlink(url, label, target="_blank"))
        return results


@register_tool(
    url_name='tools:site_search',
    index_label='Datenbank durchsuchen',
    superuser_only=False
)
class MIZSiteSearch(MIZAdminMixin, SiteSearchView):
    app_label = 'dbentry'

    title = 'Datenbank durchsuchen'
    breadcrumbs_title = 'Suchen'

    def _get_models(self, app_label: str = '') -> List[Model]:
        # Limit the models to those subclassing BaseModel only.
        from dbentry.base.models import BaseModel, BaseM2MModel  # avoid circular imports
        # noinspection PyTypeChecker
        return [
            m for m in super()._get_models(app_label)
            if issubclass(m, BaseModel) and not issubclass(m, BaseM2MModel)
        ]

    def _search(self, model: Model, q: str) -> Any:
        # noinspection PyUnresolvedReferences
        return model.objects.search(q, ranked=False)  # pragma: no cover


class SearchbarSearch(MIZSiteSearch):

    def get(self, request: HttpRequest, **kwargs: Any) -> JsonResponse:
        if q := request.GET.get('q', ''):
            results = self.get_result_list(q)
        else:
            results = []
        return JsonResponse({'results': results})
