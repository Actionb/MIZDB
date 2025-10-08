from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.admin.utils import unquote
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView

from dbentry.site.views.base import PAGE_VAR, ModelViewMixin
from dbentry.utils import permission as perms


# TODO: handle invalid pk / object does not exist
#  This causes an error if a user tries to access this view for an object that
#  does not exist.
class HistoryView(PermissionRequiredMixin, ModelViewMixin, ListView):
    title = "Änderungsgeschichte"
    template_name = "mizdb/object_history.html"
    paginate_by = 100
    page_kwarg = PAGE_VAR

    def get_queryset(self):
        return (
            LogEntry.objects.filter(
                object_id=unquote(self.kwargs.get(self.pk_url_kwarg)),
                content_type=get_content_type_for_model(self.model),
            )
            .select_related()
            .order_by("action_time")
        )

    def has_permission(self):
        return perms.has_view_permission(self.request.user, self.opts)

    def get_context_data(self, **kwargs):  # pragma: no cover
        obj = get_object_or_404(self.model, pk=unquote(self.kwargs.get(self.pk_url_kwarg)))
        ctx = super().get_context_data(**kwargs)
        paginator = self.get_paginator(self.get_queryset(), 100)
        page_number = self.request.GET.get(self.page_kwarg, 1)
        page_obj = paginator.get_page(page_number)
        page_range = paginator.get_elided_page_range(page_obj.number)
        ctx = {
            **ctx,
            "paginator": paginator,
            "page_number": page_number,
            "page_obj": page_obj,
            "page_range": page_range,
            "page_var": self.page_kwarg,
            "pagination_required": paginator.count > 100,
            "title": f"{self.title}: {str(obj)}",
        }
        return ctx
