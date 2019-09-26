from itertools import chain

from django import views
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse

from DBentry import utils
from DBentry.actions.views import MergeViewWizarded
from DBentry.base.views import MIZAdminMixin
from DBentry.sites import register_tool, miz_site
from DBentry.maint.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm
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

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
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

    site_title = 'Duplikate finden'
    next_view = 'dupes'


class DuplicateObjectsView(MaintViewMixin, views.generic.FormView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not kwargs.get('model_name'):
            raise TypeError("Model not provided.")
        self.model = utils.get_model_from_string(kwargs['model_name'])
        if self.model is None:
            raise ValueError("Unknown model: %s" % kwargs['model_name'])
        self.opts = self.model._meta
        # 'title' is a context variable for base_site.html:
        # together with 'site_title' it makes up the <title> section of a page.
        self.title = 'Duplikate: ' + self.opts.verbose_name
        self.breadcrumbs_title = self.opts.verbose_name

    def get(self, request, *args, **kwargs):
        """Handle the request to find duplicates."""
        form = self.get_form()
        context = self.get_context_data(form, **kwargs)
        if 'get_duplicates' in request.GET and form.is_valid():
            context['headers'] = self.build_duplicates_headers(form)
            context['items'] = self.build_duplicates_items(form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """Handle the request to merge duplicates."""
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        if selected:
            # Items to be merged are selected, call the MergeViewWizarded view.
            response = MergeViewWizarded.as_view(
                model_admin=miz_site.get_admin_model(self.model),
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
            duplicate_values = [
                values[field_name][0]
                for field_name in dupe_fields
                if field_name in values
            ]
            # 'dupe_item' contains the data required to create a 'row' for the
            # table listing the duplicates. It contains the model instance that
            # is part of this 'duplicates group', a link to the instance's change
            # page and the values that are shared in the 'duplicates group'.
            dupe_item = [
                (
                    instance,
                    utils.get_obj_link(
                        instance, self.request.user, include_name=False),
                    duplicate_values
                )
                for instance in dupe.instances
            ]
            # Add a link to the changelist page of this group.
            view_name = 'admin:{}_{}_changelist'.format(
                self.opts.app_label, self.opts.model_name
            )
            cl_url = reverse(view_name)
            cl_url += '?id__in={}'.format(
                ",".join([str(instance.pk) for instance in dupe.instances])
            )
            items.append((dupe_item, cl_url))
        return items
