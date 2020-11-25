from django.contrib.admin.views.main import ChangeList, ORDER_VAR

from DBentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):

    def get_queryset(self, request):
        # NOTE: list_prefetch_related currently not used anywhere
        # Add queryset optimization:
        if getattr(self.model_admin, 'list_prefetch_related', None):
            return super().get_queryset(request).prefetch_related(
                *self.model_admin.list_prefetch_related)
        return super().get_queryset(request)

    def get_results(self, request):
        super().get_results(request)
        # Add annotations required for this model admin's 'list_display' items.
        annotations = self.model_admin.get_result_list_annotations()
        if annotations:
            self.result_list = self.result_list.annotate(**annotations)


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
