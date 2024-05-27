from django.urls import include, path

from dbentry import models as _models
from dbentry.admin.autocomplete import views
from dbentry.admin.autocomplete.widgets import GENERIC_URL_NAME

autocomplete_patterns = [
    path('autor/', views.ACAutor.as_view(), name='acautor'),
    path('ausgabe/', views.ACAusgabe.as_view(), name='acausgabe'),
    path('band/', views.ACBand.as_view(), name='acband'),
    path('band/<str:create_field>/', views.ACBand.as_view(), name='acband'),
    path('buch/', views.ACBuchband.as_view(), name='acbuchband'),
    path('magazin/', views.ACMagazin.as_view(), name='acmagazin'),
    path('magazin/<str:create_field>/', views.ACMagazin.as_view(), name='acmagazin'),
    path('musiker/', views.ACMusiker.as_view(), name='acmusiker'),
    path('musiker/<str:create_field>/', views.ACMusiker.as_view(), name='acmusiker'),
    path('person/', views.ACPerson.as_view(), name='acperson'),
    path('spielort/', views.ACSpielort.as_view(), name='acspielort'),
    path('veranstaltung/', views.ACVeranstaltung.as_view(), name='acveranstaltung'),
    path('genre/', views.ACMostUsed.as_view(model=_models.Genre), name='acgenre'),
    path('genre/<str:create_field>/', views.ACMostUsed.as_view(model=_models.Genre), name='acgenre'),
    path('schlagwort/', views.ACMostUsed.as_view(model=_models.Schlagwort), name='acschlagwort'),
    path('schlagwort/<str:create_field>/', views.ACMostUsed.as_view(model=_models.Schlagwort), name='acschlagwort'),
    path('gnd/', views.GND.as_view(), name='gnd'),
    path('auth_user/', views.UserAutocompleteView.as_view(), name='autocomplete_user'),
    path('content_type/', views.ContentTypeAutocompleteView.as_view(), name='autocomplete_ct'),
    # TODO: enable the lagerort autocomplete URL (see views.ACLagerort for more details)
    # path('lagerort/', views.ACLagerort.as_view(), name='aclagerort'),
]
# noinspection SpellCheckingInspection

urlpatterns = [
    path('', include(autocomplete_patterns)),
    path('<str:model_name>/<str:create_field>/', views.ACBase.as_view(), name=GENERIC_URL_NAME),
    path('<str:model_name>/', views.ACBase.as_view(), name=GENERIC_URL_NAME)
]
