from django.urls import path

from dbentry.help.views import HelpView, HelpIndex

urlpatterns = [
    path("", HelpIndex.as_view(), name="help_index"),
    path("<str:title>/", HelpView.as_view(), name="help"),
]
