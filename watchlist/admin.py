from watchlist.views import get_watchlist


class WatchlistAdminMixin(object):
    # TODO: include this in MIZAdmin - the checkbox won't be accurate without it

    def on_watchlist(self, request, object_id):
        watchlist = get_watchlist(request)
        if self.opts.label not in watchlist:
            return False
        return int(object_id) in [pk for pk, time_added in watchlist[self.opts.label]]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """View for changing an object."""
        if extra_context is None:
            extra_context = {}
        # Add an indicator whether this instance is on the watchlist:
        extra_context['on_watchlist'] = self.on_watchlist(request, object_id)
        return super().change_view(request, object_id, form_url, extra_context)

