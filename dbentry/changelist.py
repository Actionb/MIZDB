from django.contrib.admin.views.main import ALL_VAR, ChangeList, ORDER_VAR
from django.db.models import QuerySet
from django.http import HttpRequest

from dbentry.search.admin import ChangelistSearchFormMixin
from dbentry.utils import get_model_fields


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


class BestandChangeList(ChangeList):

    def get_results(self, request: HttpRequest) -> None:
        super().get_results(request)
        # Include the related archive objects referenced by the Bestand objects
        # (i.e. Ausgabe, Audio, etc.) in the result queryset.
        bestand_fields = [
            f for f in get_model_fields(self.model, base=False, foreign=True, m2m=False)
            if f.related_model._meta.model_name not in ('lagerort', 'provenienz')
        ]
        # Let the model admin cache the data it needs for the list display
        # items 'bestand_class' and 'bestand_link'.
        self.model_admin.cache_bestand_data(
            request,
            self.result_list.select_related(*[f.name for f in bestand_fields]),  # type: ignore[has-type]  # noqa
            bestand_fields
        )
        # Overwrite the result_list.
        self.result_list = self.result_list.select_related(  # type: ignore[has-type]
            *self.list_select_related,
            *[f.name for f in bestand_fields]
        )
