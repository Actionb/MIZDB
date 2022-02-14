from django.urls import path

from watchlist.views import WatchlistView, watchlist_changelist, watchlist_toggle

urlpatterns = [
    path('watchlist_toggle', watchlist_toggle, name='watchlist_toggle'),
    path(
        'watchlist_changelist/<str:app_label>/<str:model_name>',
        watchlist_changelist, name='watchlist_changelist'
    ),
    path('watchlist', WatchlistView.as_view(), name='watchlist'),
]