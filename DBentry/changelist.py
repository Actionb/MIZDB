from django.contrib.admin.views.main import ChangeList

from DBentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):

    def get_queryset(self, request):
        # Add queryset optimization:
        if getattr(self.model_admin, 'list_prefetch_related', None):
            return super().get_queryset(request).prefetch_related(
                *self.model_admin.list_prefetch_related)
        return super().get_queryset(request)


class AusgabeChangeList(MIZChangeList):

    def get_queryset(self, request):
        """Apply chronologic_order to the result queryset."""
        return super().get_queryset(request).chronologic_order()
