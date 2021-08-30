from django.contrib.admin.views.main import ChangeList, ALL_VAR, ORDER_VAR

from dbentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):

    def get_results(self, request):
        # A changelist with many, many items needs to be filtered to be of any
        # real use. If the changelist's queryset is unfiltered, only show
        # results if either:
        #   - ALL_VAR is present in the request: which means the user has
        #       clicked the 'total count' link on the changelist, i.e. an
        #       unfiltered result list is intentionally requested
        #   - the model admin does not provide a search form: the changelist
        #       page would look very empty without either a result list or a
        #       search form; the user might think this is an error
        if not self.queryset.query.has_filters():
            if self.model_admin.has_search_form() and not self.show_all:
                self.queryset = self.queryset.none()
        super().get_results(request)
        # Add annotations required for this model admin's 'list_display' items.
        annotations = self.model_admin.get_result_list_annotations()
        if annotations:
            self.result_list = self.result_list.annotate(**annotations)

    def get_show_all_url(self):
        """Return the url for an unfiltered changelist showing all objects."""
        return self.get_query_string(
            new_params={ALL_VAR: ''}, remove=self.params)


class AusgabeChangeList(MIZChangeList):

    def get_queryset(self, request):
        """
        Apply chronological_order to the result queryset unless manually-specified
        ordering is available from the query string.
        """
        if ORDER_VAR in self.params:
            return super().get_queryset(request)
        else:
            return super().get_queryset(request).chronological_order()
