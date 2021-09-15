from django.contrib.admin.views.main import ALL_VAR, ChangeList, ORDER_VAR
from django.db.models import QuerySet
from django.http import HttpRequest

from dbentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):

    def get_results(self, request: HttpRequest) -> None:
        """
        Prepare the result list of the changelist.

        If the changelist's queryset is unfiltered, only show results if either:
            - ``ALL_VAR`` is present in the request: which means the user has
              clicked the 'total count' link on the changelist, i.e. an
              unfiltered result list is explicitly requested
            - the model admin does not provide a search form: the changelist
              page would look very empty without either a result list or a
              search form; the user might think this is an error
        """
        if not self.queryset.query.has_filters():  # type: ignore[has-type]
            if self.model_admin.has_search_form() and not self.show_all:
                self.queryset = self.queryset.none()  # type: ignore[has-type]
        # Let ChangeList.get_results set some other attributes:
        super().get_results(request)
        # Add annotations required for this model admin's 'list_display' items.
        annotations = self.model_admin.get_result_list_annotations()
        if annotations:
            # noinspection PyAttributeOutsideInit
            self.result_list = self.result_list.annotate(**annotations)  # type: ignore[has-type]

    def get_show_all_url(self) -> str:
        """Return the url for an unfiltered changelist showing all objects."""
        return self.get_query_string(
            new_params={ALL_VAR: ''}, remove=self.params
        )


class AusgabeChangeList(MIZChangeList):

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Apply chronological order to the result queryset unless an ordering is
        specified in the query string.
        """
        if ORDER_VAR in self.params:
            return super().get_queryset(request)
        else:
            return super().get_queryset(request).chronological_order()
