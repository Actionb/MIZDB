from django.contrib.admin.views.main import ChangeList

from DBentry.search.admin import ChangelistSearchFormMixin


class MIZChangeList(ChangelistSearchFormMixin, ChangeList):
    pass


class AusgabeChangeList(MIZChangeList):

    def get_queryset(self, request):
        """Apply chronologic_order to the result queryset."""
        return super().get_queryset(request).chronologic_order()
