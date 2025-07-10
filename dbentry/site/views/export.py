from django.db import models
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.views.generic import FormView
from import_export.mixins import ExportViewMixin
from import_export.signals import post_export

from dbentry.actions.base import ActionConfirmationView
from dbentry.export.base import get_verbose_name_for_resource_field
from dbentry.export.forms import MIZSelectableFieldsExportForm
from dbentry.site.views.base import ModelViewMixin
from dbentry.utils.permission import has_export_permission


class BaseExportView(UserPassesTestMixin, ModelViewMixin, ExportViewMixin, FormView):
    """Base view for exporting model objects."""

    queryset: models.QuerySet = None
    form_class = MIZSelectableFieldsExportForm

    title: str = "Export"

    def get_queryset(self):
        return self.queryset

    def get_export_resource(self):  # pragma: no cover
        return self.resource_classes[0]()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["queryset"] = self.get_queryset()
        return ctx

    def test_func(self) -> bool:  # pragma: no cover
        """test_func for UserPassesTestMixin."""
        return has_export_permission(self.request.user, self.get_queryset().model._meta)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["choices"] = {}
        fields_choices = []
        resource = self.get_export_resource()
        for field_name in resource.get_export_order():
            fields_choices.append((field_name, get_verbose_name_for_resource_field(resource, field_name)))
        kwargs["choices"]["fields_select"] = fields_choices
        return kwargs

    def get_export_resource_fields_from_form(self, form):
        return form.cleaned_data.get("fields_select")

    def form_valid(self, form):
        # Originally, this was part of the ExportViewFormMixin from
        # django-import-export, but that mixin has been slated for deprecation.
        formats = self.get_export_formats()
        file_format = formats[int(form.cleaned_data["format"])]()
        export_data = self.get_export_data(file_format, self.get_queryset(), export_form=form)
        content_type = file_format.get_content_type()
        response = HttpResponse(export_data, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{self.get_export_filename(file_format)}"'
        post_export.send(sender=None, model=self.model)
        return response


class ExportActionView(BaseExportView, ActionConfirmationView):
    """Export a queryset via a changelist action."""

    action_name: str = "export"
    template_name: str = "mizdb/export.html"

    def post(self, request, *args, **kwargs):
        if self.action_confirmed(request):
            # User confirmed the export.
            return super().post(request, *args, **kwargs)
        else:
            # This POST request was issued from the changelist.
            # Show the confirmation page.
            return self.get(request, *args, **kwargs)


class ExportModelView(BaseExportView):
    """Export all objects of the view's model."""

    model: type[models.Model] = None  # type: ignore[assignment]
    template_name: str = "mizdb/export_model.html"

    def get_queryset(self):  # pragma: no cover
        return self.model.objects.all()

    def test_func(self) -> bool:
        return self.request.user.is_superuser


class ExportResultsActionView(ExportActionView):
    """Exports all objects of a filtered changelist."""

    action_name = "export_results"
    # The queryset to export is the same as the changelist's queryset. As such,
    # the template need not render a hidden field for each of the 'selected
    # items' like for ExportActionView.
    template_name: str = "mizdb/export_results.html"
