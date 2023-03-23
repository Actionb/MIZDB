from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.admin.utils import unquote
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin

from dbentry.site.views.base import ModelViewMixin
from dbentry.utils import permission as perms


class HistoryView(PermissionRequiredMixin, ModelViewMixin, SingleObjectMixin, TemplateView):
    title = "Änderungsgeschichte"
    template_name = "mizdb/object_history.html"

    def has_permission(self):
        return perms.has_view_permission(self.request.user, self.opts)

    def get_history(self):
        """Get the history of this view's object."""
        return (
            LogEntry.objects.filter(
                object_id=unquote(self.kwargs.get(self.pk_url_kwarg)),
                content_type=get_content_type_for_model(self.model),
            )
            .select_related()
            .order_by("action_time")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['history'] = self.get_history()
        return ctx
