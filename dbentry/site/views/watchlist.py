from django.views.generic import TemplateView
from mizdb_watchlist.views import WatchlistViewMixin

from dbentry.models import Ausgabe
from dbentry.site.views import BaseViewMixin


class WatchlistView(WatchlistViewMixin, BaseViewMixin, TemplateView):
    template_name = "mizdb/watchlist.html"
    title = "Merkliste"

    def get_object_text(self, request, model, pk, object_repr=""):
        if model == Ausgabe:
            obj = model.objects.select_related("magazin").get(pk=pk)
            return f"{str(obj)} ({str(obj.magazin)})"
        return super().get_object_text(request, model, pk, object_repr)
