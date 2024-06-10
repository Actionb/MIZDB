from django.contrib.auth.mixins import UserPassesTestMixin
from import_export.mixins import ExportViewFormMixin

from dbentry.actions.base import ActionConfirmationView
from dbentry.site.views.base import ModelViewMixin


def has_export_permission(user, opts):  # pragma: no cover
    return user.is_superuser


class BaseExportView(UserPassesTestMixin, ModelViewMixin, ExportViewFormMixin):
    """Base view for exporting model objects."""

    queryset = None

    title = "Export"

    def get_queryset(self):
        return self.queryset

    def get_export_resource(self):  # pragma: no cover
        return self.resource_class()

    def get_data_for_export(self, request, queryset, *args, **kwargs):  # pragma: no cover
        return self.get_export_resource().export(*args, queryset=queryset, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["queryset"] = self.get_queryset()
        return ctx

    def test_func(self) -> bool:  # pragma: no cover
        """test_func for UserPassesTestMixin."""
        return has_export_permission(self.request.user, self.get_queryset().model._meta)


class ExportActionView(BaseExportView, ActionConfirmationView):
    """Export a queryset."""

    action_name = "export"
    template_name = "mizdb/export.html"

    def post(self, request, *args, **kwargs):
        if self.action_confirmed(request):
            # User confirmed the export.
            return super().post(request, *args, **kwargs)
        else:
            # This POST request was issued from the changelist selection panel.
            # Show the confirmation page.
            return self.get(request, *args, **kwargs)


class ExportModelView(BaseExportView):
    """Export all objects of the view's model."""

    model = None
    template_name = "mizdb/export_model.html"

    def get_queryset(self):  # pragma: no cover
        return self.model.objects.all()
