from itertools import chain
from collections import OrderedDict

from django import views
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q, Count
from django.shortcuts import redirect
from django.urls import reverse

from DBentry import utils
from DBentry.actions.views import MergeViewWizarded
from DBentry.base.views import MIZAdminMixin
from DBentry.sites import register_tool
from DBentry.maint.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm, UnusedObjectsForm
)


class MaintViewMixin(MIZAdminMixin, UserPassesTestMixin):
    """
    Simple mixin that provides django-admin looks from MIZAdminMixin and access
    restrictions from UserPassesTestMixin.
    """

    def test_func(self):
        """
        test_func for UserPassesTestMixin.
        Only allow superusers to access the view.
        """
        return self.request.user.is_superuser


class ModelSelectView(views.generic.FormView):
    """
    A FormView that redirects to another view with the model chosen in the form
    as initkwargs.

    Attributes:
        next_view (str): reverseable view name of the next view.
    """

    template_name = 'admin/basic.html'  # a very generic template
    submit_value = 'Weiter'
    submit_name = 'submit'
    form_method = 'get'

    form_class = ModelSelectForm
    next_view = 'admin:index'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add context variables specific to admin/basic.html:
        context['submit_value'] = self.submit_value
        context['submit_name'] = self.submit_name
        context['form_method'] = self.form_method
        return context

    def get(self, request, *args, **kwargs):
        if self.submit_name in request.GET:
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(self.next_view, kwargs=self.get_next_view_kwargs())

    def get_next_view_kwargs(self):
        return {'model_name': self.request.GET.get('model_select')}


class ModelSelectNextViewMixin(MaintViewMixin):
    """A mixin that sets up the view following a ModelSelectView."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not kwargs.get('model_name'):
            raise TypeError("Model not provided.")
        self.model = utils.get_model_from_string(kwargs['model_name'])
        if self.model is None:
            raise ValueError("Unknown model: %s" % kwargs['model_name'])
        self.opts = self.model._meta

    def get_context_data(self, **kwargs):
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
class DuplicateModelSelectView(MaintViewMixin, ModelSelectView):
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
    and the possiblity for merging each group is provided.
    """

    template_name = 'admin/dupes.html'
    form_class = DuplicateFieldsSelectForm

    def get(self, request, *args, **kwargs):
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

    def post(self, request, *args, **kwargs):
        """Handle the request to merge duplicates."""
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        if selected:
            # Items to be merged are selected, call the MergeViewWizarded view.
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

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        media = context.get('media')
        if media:
            media += form.media
        else:
            media = form.media
        context['media'] = utils.ensure_jquery(media)
        context['action_name'] = 'merge_records'
        context['action_checkbox_name'] = ACTION_CHECKBOX_NAME
        # 'title' is a context variable for base_site.html:
        # together with 'site_title' it makes up the <title> section of a page.
        context['title'] = 'Duplikate: ' + self.opts.verbose_name
        return context

    def get_form_kwargs(self):
        """Return the kwargs for the fields select form."""
        kwargs = super().get_form_kwargs()
        kwargs['model'] = self.model
        kwargs['data'] = self.request.GET
        return kwargs

    def build_duplicates_headers(self, form):
        """
        Prepare the headers from the selected search fields in 'form' for the
        table that lists the duplicates.
        The headers should be the human readable part of the choices.
        """
        headers = []
        # Iterate over form.fields instead of form.cleaned_data to preserve
        # ordering.
        for field_name, formfield in form.fields.items():
            selected = form.cleaned_data.get(field_name)
            if not selected:
                continue
            choices = formfield.choices
            if isinstance(choices[0][1], (list, tuple)):
                # Grouped choices: [('group_name',[*choices]), ...].
                # Get the actual choices:
                choices = chain(*(
                    group_choices
                    for group_name, group_choices in choices
                ))
            # Acquire the human readable parts of the choices that have been
            # selected:
            headers.extend(
                human_readable
                for value, human_readable in choices
                if value in selected
            )
        return headers

    def build_duplicates_items(self, form):
        """Prepare the content of the table that lists the duplicates."""
        # Get the model fields that were selected in the form.
        dupe_fields = []
        for field_name in form.fields:
            if form.cleaned_data.get(field_name):
                dupe_fields.extend(form.cleaned_data[field_name])
        # Look for duplicates using the selected fields.
        # A list of namedtuples is returned, each with attributes:
        # - 'instances': a list of instances that are duplicates of each other
        # - 'values': a list of field_name, field_values pairs. The values are
        #       shared by all duplicates.
        # Items in the list returned by duplicates() can be thought of as
        # 'groups' of duplicates.
        duplicates = self.model.objects.duplicates(*dupe_fields)
        items = []
        for dupe in duplicates:
            # Prepare the duplicate values.
            # dupe_fields uses the order of form.fields and thus shares the
            # same order as the headers.
            values = dict(dupe.values)
            duplicate_values = []
            for field_name in dupe_fields:
                if field_name in values:
                    duplicate_values.append(values[field_name][0])
                else:
                    # Don't skip a column! Add an 'empty'.
                    duplicate_values.append("")

            # 'dupe_item' contains the data required to create a 'row' for the
            # table listing the duplicates. It contains the model instance that
            # is part of this 'duplicates group', a link to the instance's change
            # page and the values that are shared in the 'duplicates group'.
            dupe_item = [
                (
                    instance,
                    utils.get_obj_link(instance, self.request.user, blank=True),
                    duplicate_values
                )
                for instance in dupe.instances
            ]
            # Add a link to the changelist page of this group.
            cl_url = utils.get_changelist_url(
                self.model, self.request.user, obj_list=dupe.instances)
            items.append((dupe_item, cl_url))
        return items


@register_tool(
    url_name='find_unused',
    index_label='Selten verwendete Datensätze finden',
    superuser_only=True
)
class UnusedObjectsView(MaintViewMixin, views.generic.FormView):
    """
    View that enables finding objects of a given model that are referenced by
    reversed related models less than a given limit.
    """

    form_class = UnusedObjectsForm
    template_name = 'admin/find_unused.html'
    breadcrumbs_title = title = 'Selten verwendete Datensätze finden'

    def get(self, request, *args, **kwargs):
        """Handle the request to find unused objects."""
        context = self.get_context_data(**kwargs)
        if 'get_unused' in request.GET:
            form = self.form_class(data=request.GET)
            if form.is_valid():
                model_name = form.cleaned_data['model_select']
                model = utils.get_model_from_string(model_name)
                if model is None:
                    raise ValueError("Unknown model: %s" % model_name)
                context_kwargs = {
                    'form': form,
                    'items': self.build_items(model, form.cleaned_data['limit'])
                }
                context.update(**context_kwargs)
        return self.render_to_response(context)

    def get_queryset(self, model, limit):
        """
        Prepare the queryset that includes all objects of 'model' that have less
        than 'limit' reverse related objects.

        Returns:
            - a dictionary containing information to each reverse relation
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
                c=Count(query_name)).filter(Q(c__lte=limit))
            counts = {pk: c for pk, c in qs.values_list('pk', 'c')}
            # Remove the ids of the objects that exceed the limit for this relation.
            unused.difference_update(all_ids.difference(counts))
            relations[rel] = {
                'related_model': related_model,
                'counts': counts
            }
        return relations, model.objects.filter(pk__in=unused)

    def build_items(self, model, limit):
        """Build items for the context."""
        items = []
        under_limit_template = '{model_name} ({count!s})'
        relations, queryset = self.get_queryset(model, limit)
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
            items.append((
                utils.get_obj_link(obj, user=self.request.user),
                ", ".join(sorted(under_limit))
            ))
        return items
