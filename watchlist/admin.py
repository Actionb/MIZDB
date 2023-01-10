from django import forms
from django.conf import settings

from watchlist.views import get_watchlist


class WatchlistAdminMixin(object):

    change_form_template = 'admin/watchlist/change_form.html'

    @property
    def media(self):
        media = super().media
        extra = '' if settings.DEBUG else '.min'
        js = ['vendor/jquery/jquery%s.js' % extra, 'jquery.init.js', 'watchlist.js']
        return media + forms.Media(
            js=['admin/js/%s' % url for url in js],
            css={'all': ['admin/css/watchlist.css']}
        )

    def on_watchlist(self, request, object_id):
        watchlist = get_watchlist(request)
        if self.opts.label_lower not in watchlist:
            return False
        return int(object_id) in [pk for pk, time_added in watchlist[self.opts.label_lower]]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """View for changing an object."""
        if extra_context is None:
            extra_context = {}
        # Add an indicator whether this instance is on the watchlist:
        extra_context['on_watchlist'] = self.on_watchlist(request, object_id)
        return super().change_view(request, object_id, form_url, extra_context)

