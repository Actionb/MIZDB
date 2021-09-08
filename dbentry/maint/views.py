from collections import Counter, OrderedDict, namedtuple
from itertools import chain
from typing import Any, Dict, List, Sequence, Tuple, Type, Union

from django import views
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db.models import Count, ManyToManyRel, ManyToOneRel, Model, OneToOneRel, Q, QuerySet
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import SafeText

from dbentry import utils
from dbentry.actions.views import MergeViewWizarded
from dbentry.base.views import MIZAdminMixin, SuperUserOnlyMixin
from dbentry.maint.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm, UnusedObjectsForm
)
from dbentry.sites import register_tool

Relations = Union[ManyToManyRel, ManyToOneRel, OneToOneRel]

Dupe = namedtuple(
    'Dupe', ['instance', 'duplicate_values', 'display_values']
)


def find_duplicates(
        queryset: QuerySet,
        dupe_fields: Sequence[str],
        display_fields: Sequence[str]
) -> List[List[Dupe]]:
    """
    Find records in the queryset that share values in the fields given
    by dupe_fields.

    Returns a list of lists (groups of duplicates) where each list is made up of
    'Dupe' named tuples.

    'Dupe' has three attributes:
        - instance: the model instance that is a duplicate of another
        - duplicate_values: the values that are shared
        - display_values: the values fetched to be displayed
    """

    # noinspection PyUnresolvedReferences
    queried: OrderedDict[int, Tuple[str, Any]] = queryset.values_dict(
        *dupe_fields, *display_fields, tuplfy=True
    )
    dupe_values: List[tuple] = []
    display_values: Dict[int, list] = {}
    # Separate duplicate_values and display_values which are both contained
    # (as tuples) in the following tuple 'values':
    for pk, values in queried.items():
        item_dupe_values = []
        for k, v in values:
            if k in dupe_fields:
                item_dupe_values.append((k, v))
            elif k in display_fields:
                if pk not in display_values:
                    display_values[pk] = []
                display_values[pk].append((k, v))
        dupe_values.append(tuple(item_dupe_values))

    results: List[List[Dupe]] = []
    # Walk through the values, looking for non-empty values that appeared
    # more than once.
    # Preserve the display_values.
    for elem, count in Counter(dupe_values).items():
        dupe_group: List[Dupe] = []
        if not elem or count < 2:
            # Do not compare empty with empty.
            continue
        # Find all the pks that match these values.
        for pk, values in queried.items():
            item_dupe_values = tuple(  # type: ignore[assignment]
                (k, v) for k, v in values if k in dupe_fields
            )
            if elem == item_dupe_values:
                item_display_values = dict(display_values.get(pk, ()))
                dupe_group.append(
                    Dupe(
                        instance=queryset.get(pk=pk),
                        duplicate_values=dict(item_dupe_values),
                        display_values=item_display_values
                    )
                )
        results.append(dupe_group)
    return results


class ModelSelectView(views.generic.FormView):
    """
    A FormView that redirects to another view with the model chosen in the form
    as initkwargs.

    Attributes:
        - ``next_view`` (str): view name of the next view. reverse() must be
          able to return an URL using this view name.
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


class ModelSelectNextViewMixin(MIZAdminMixin, SuperUserOnlyMixin):
    """A mixin that sets up the view following a ModelSelectView."""

    # noinspection PyAttributeOutsideInit
    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        # noinspection PyUnresolvedReferences
        super().setup(request, *args, **kwargs)
        if not kwargs.get('model_name'):
            raise TypeError("Model not provided.")
        self.model = utils.get_model_from_string(kwargs['model_name'])
        if self.model is None:
            raise ValueError("Unknown model: %s" % kwargs['model_name'])
        # noinspection PyUnresolvedReferences,PyProtectedMember
        self.opts = self.model._meta

    def get_context_data(self, **kwargs: Any) -> dict:
        return super().get_context_data(
            breadcrumbs_title=self.opts.verbose_name,
            title=self.opts.verbose_name,
            **kwargs
        )


@register_tool(
    url_name='dupes_select',
    index_label='Duplikate finden',
    superuser_only=True
)
class DuplicateModelSelectView(MIZAdminMixin, SuperUserOnlyMixin, ModelSelectView):
    """
    Main entry point for the duplicates search.

    It let's the user choose a model to search for duplicates in and then
    redirects to the DuplicateObjectsView.
    """

    title = 'Duplikate finden'
    next_view = 'dupes'


class DuplicateObjectsView(ModelSelectNextViewMixin, views.generic.FormView):
    """
    A FormView that finds, displays and, if so requested, merges duplicates.

    The view's form contains the model fields with which a search for duplicates
    is done. Duplicates are model instances that have the same values in all of
    the model fields selected in the form.
    These duplicates are grouped together according to these equivalent values
    and the possibility for merging each group is provided.
    """

    template_name = 'admin/dupes.html'
    form_class = DuplicateFieldsSelectForm

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle the request to find duplicates."""
        form = self.get_form()
        context = self.get_context_data(form=form, **kwargs)
        if 'get_duplicates' in request.GET and form.is_valid():
            context['headers'] = self.build_duplicates_headers(form)
            # Calculate the (percentile) width of the headers; 25% of the width
            # is already taken up by the three headers 'merge','id','link'.
            context['headers_width'] = str(int(75 / len(context['headers'])))
            context['items'] = self.build_duplicates_items(form)
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle the request to merge duplicates."""
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        if selected:
            # Items to be merged are selected, call the MergeViewWizarded view.
            # noinspection PyUnresolvedReferences
            response = MergeViewWizarded.as_view(
                model_admin=utils.get_model_admin_for_model(self.model),
                queryset=self.model.objects.filter(pk__in=selected)
            )(request)
            if response:
                # MergeViewWizarded has returned a response:
                # the merge conflict resolution page.
                return response
        # MergeViewWizarded returned None (successful merge)
        # or there was nothing selected: redirect back here.
        return redirect(request.get_full_path())

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context['action_name'] = 'merge_records'
        context['action_checkbox_name'] = ACTION_CHECKBOX_NAME
        # 'title' is a context variable for base_site.html:
        # together with 'site_title' it makes up the <title> section of a page.
        context['title'] = 'Duplikate: ' + self.opts.verbose_name
        return context

    def get_form_kwargs(self) -> dict:
        """Return the kwargs for the fields select form."""
        kwargs = super().get_form_kwargs()
        kwargs['model'] = self.model
        kwargs['data'] = self.request.GET
        return kwargs

    @staticmethod
    def _get_group_field_names(form, formfield_group: List[str]) -> List[str]:
        """
        Return the field names of fields selected in the given formfield_group.

        Check the given formfield_group (i.e. either select_fields or
        display_fields) and create a list of all model field names selected in
        that group.
        """
        field_names = []
        for formfield_name in formfield_group:
            if form.cleaned_data.get(formfield_name):
                field_names.extend(form.cleaned_data[formfield_name])
        return field_names

    def get_select_fields(self, form: Form) -> List[str]:
        """Return a list of the field names the user selected to be displayed."""
        return self._get_group_field_names(form, form.select_fields)

    def get_display_fields(self, form: Form) -> List[str]:
        """Return a list of the field names the user selected to be displayed."""
        return self._get_group_field_names(form, form.display_fields)

    # noinspection PyMethodMayBeStatic
    def build_duplicates_headers(self, form: Form) -> List[str]:
        """
        Extract the table headers for the table that lists the duplicates from
        the selected display fields in 'form'.
        The headers should be the human readable part of the choices.
        """
        headers: List[str] = []
        for field_name in form.display_fields:
            formfield = form.fields[field_name]
            selected = form.cleaned_data.get(field_name)
            if not selected:
                continue
            choices = formfield.choices
            if isinstance(choices[0][1], (list, tuple)):
                # Grouped choices: [('group_name',[*choices]), ...].
                # Get the actual choices:
                choices = chain(
                    *(
                        group_choices
                        for group_name, group_choices in choices
                    )
                )
            # Acquire the human readable parts of the choices that have been
            # selected:
            headers.extend(
                human_readable
                for value, human_readable in choices
                if value in selected
            )
        return headers

    # noinspection PyUnresolvedReferences
    def build_duplicates_items(
            self, form: Form
    ) -> List[Tuple[List[Tuple[Any, SafeText, List[str]]], SafeText]]:
        """
        Prepare the content of the table that lists the duplicates.

        Returns a list of 2-tuples, where the first item is a list of
        (model instance, change page URL, display values) tuples, and the last
        item is the link to the changelist of the duplicate instances.
        """
        items = []
        # Get the model fields that were selected in the form.
        dupe_fields = self.get_select_fields(form)
        display_fields = self.get_display_fields(form)
        # Look for duplicates using the selected fields.
        # A list of lists/group of 'Dupe' named tuples is returned.
        duplicates = find_duplicates(self.model.objects, dupe_fields, display_fields)
        # Walk through each group of duplicates:
        for dupe_group in duplicates:
            group = []
            instances = []
            for dupe in dupe_group:
                # 'Dupe' has these attributes:
                # - 'instance': the duplicate model instance
                # - 'duplicate_values': a list of field_name, field_values pairs
                #       the values are shared by the duplicates
                # - 'display_values': additional values for the tables
                # Create a list of string values to display on the table.
                display_values = []
                for field_name in display_fields:
                    if field_name in dupe.duplicate_values:
                        values = dupe.duplicate_values[field_name]
                    elif field_name in dupe.display_values:
                        values = dupe.display_values[field_name]
                    else:
                        values = []
                    display_values.append(
                        ", ".join(str(v)[:100] for v in values)
                    )
                # Add this instance's data, including a change link, to the group.
                group.append(
                    (
                        dupe.instance,
                        utils.get_obj_link(dupe.instance, self.request.user, blank=True),
                        display_values
                    )
                )
                # Record the group's instances for the changelist link.
                instances.append(dupe.instance)
            # Add a link to the changelist page of this group.
            cl_url = utils.get_changelist_url(
                self.model, self.request.user, obj_list=instances
            )
            link = utils.create_hyperlink(
                url=cl_url, content='Änderungsliste',
                **{'target': '_blank', 'class': 'button'}
            )
            items.append((group, link))
        return items


@register_tool(
    url_name='find_unused',
    index_label='Unreferenzierte Datensätze',
    superuser_only=True
)
class UnusedObjectsView(MIZAdminMixin, SuperUserOnlyMixin, ModelSelectView):
    """
    View that enables finding objects of a given model that are referenced by
    reversed related models less than a given limit.
    """

    form_class = UnusedObjectsForm
    template_name = 'admin/find_unused.html'

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
                model = utils.get_model_from_string(model_name)
                relations, queryset = self.get_queryset(model, form.cleaned_data['limit'])
                # noinspection PyUnresolvedReferences
                cl_url = utils.get_changelist_url(model, request.user, obj_list=queryset)
                context_kwargs = {
                    'form': form,
                    'items': self.build_items(relations, queryset),
                    'changelist_link': utils.create_hyperlink(
                        url=cl_url, content='Änderungsliste',
                        **{'target': '_blank', 'class': 'button'}
                    )
                }
                context.update(**context_kwargs)
        return self.render_to_response(context)

    # noinspection PyMethodMayBeStatic,PyUnresolvedReferences
    def get_queryset(
            self, model: Type[Model], limit: int
    ) -> Tuple[OrderedDict[Relations, dict], QuerySet]:
        """
        Prepare the queryset that includes all objects of ``model`` that have
        less than ``limit`` reverse related objects.

        Returns a 2-tuple:
            - a OrderedDict containing information to each reverse relation
            - queryset of the 'unused' objects
        """
        relations = OrderedDict()
        # all_ids is a 'screenshot' of all IDs of the model's objects.
        # Starting out, unused will also contain all IDs, but any ID that is
        # from an object that exceeds the limit will be removed.
        all_ids = unused = set(model.objects.values_list('pk', flat=True))

        # For each reverse relation, query for the 'unused' objects, and remove
        # all OTHER IDs (i.e. those of objects that exceed the limit) from the
        # set 'unused'.
        for rel in utils.get_model_relations(model, forward=False):
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
            qs = model.objects.order_by().annotate(
                c=Count(query_name)
            ).filter(Q(c__lte=limit))
            counts = {pk: c for pk, c in qs.values_list('pk', 'c')}
            # Remove the ids of the objects that exceed the limit for this relation.
            unused.difference_update(all_ids.difference(counts))
            relations[rel] = {
                'related_model': related_model,
                'counts': counts
            }
        return relations, model.objects.filter(pk__in=unused)

    def build_items(
            self,
            relations: OrderedDict[Relations, dict],
            queryset: QuerySet
    ) -> List[Tuple[SafeText, str]]:
        """Build items for the context."""
        items = []
        under_limit_template = '{model_name} ({count!s})'
        for obj in queryset:
            under_limit = []
            for info in relations.values():
                count = info['counts'].get(obj.pk, 0)
                # noinspection PyProtectedMember
                under_limit.append(
                    under_limit_template.format(
                        model_name=info['related_model']._meta.verbose_name,
                        count=count
                    )
                )
            items.append(
                (
                    utils.get_obj_link(obj, user=self.request.user, blank=True),
                    ", ".join(sorted(under_limit))
                )
            )
        return items
