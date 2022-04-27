from django.urls import include, path

from dbentry.ac import views

# noinspection SpellCheckingInspection
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
    path('gnd/', views.GND.as_view(), name='gnd'),
    path('auth_user/', views.UserAutocompleteView.as_view(), name='autocomplete_user'),
    path('content_type/', views.ContentTypeAutocompleteView.as_view(), name='autocomplete_ct'),
    # TODO: enable the lagerort autocomplete URL (see views.ACLagerort for more details)
    # path('lagerort/', views.ACLagerort.as_view(), name='aclagerort'),
]

urlpatterns = [
    path('', include(autocomplete_patterns)),
    path('<str:model_name>/<str:create_field>/', views.ACBase.as_view(), name='accapture'),
    path('<str:model_name>/', views.ACBase.as_view(), name='accapture')
]
