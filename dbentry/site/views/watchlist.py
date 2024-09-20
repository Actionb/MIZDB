from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import TemplateView
from mizdb_watchlist.views import WatchlistViewMixin

from dbentry import models as _models
from dbentry.site.views import BaseViewMixin


class WatchlistView(WatchlistViewMixin, BaseViewMixin, TemplateView):
    template_name = "mizdb/watchlist.html"
    title = "Merkliste"

    def get_object_text(self, request, model, pk, object_repr=""):
        if model == _models.Ausgabe:
            try:
                obj = model.objects.select_related("magazin").get(pk=pk)
                return f"{obj} ({obj.magazin})"
            except ObjectDoesNotExist:
                pass
        return super().get_object_text(request, model, pk, object_repr)
