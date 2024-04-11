from django.views.generic import TemplateView
from mizdb_watchlist.views import WatchlistViewMixin

from dbentry.site.views import BaseViewMixin


class WatchlistView(WatchlistViewMixin, BaseViewMixin, TemplateView):
    template_name = "mizdb/watchlist.html"
    title = "Merkliste"
