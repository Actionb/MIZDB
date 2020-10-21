from django.contrib.admin.views.main import ChangeList, ORDER_VAR

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
        """
        Apply chronologic_order to the result queryset unless manually-specified
        ordering is available from the query string.
        """
        if ORDER_VAR in self.params:
            return super().get_queryset(request)
        else:
            return super().get_queryset(request).chronologic_order()
