from import_export.mixins import ExportViewFormMixin

from dbentry.site.views.base import ModelViewMixin, ACTION_SELECTED_ITEM


class BaseExportView(ModelViewMixin, ExportViewFormMixin):
    queryset = None

    title = "Export"
    template_name = "mizdb/export.html"

    def get_queryset(self):
        return self.queryset

    def get_export_resource(self):
        return self.resource_class()

    def get_data_for_export(self, request, queryset, *args, **kwargs):
        return self.get_export_resource().export(*args, queryset=queryset, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["queryset"] = self.get_queryset()
        return ctx


class ExportActionView(BaseExportView):
    """Export a queryset."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_changelist_action"] = True
        ctx["action_selection_name"] = ACTION_SELECTED_ITEM
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get("post"):
            # User confirmed the export.
            return super().post(request, *args, **kwargs)
        else:
            # This POST request was issued from the changelist selection panel.
            # Show the confirmation page.
            return super().get(request, *args, **kwargs)


class ExportModelView(BaseExportView):
    """Export all objects of the view's model."""

    model = None

    def get_queryset(self):
        return self.model.objects.all()
