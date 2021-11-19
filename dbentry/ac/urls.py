from django.urls import include, path

from dbentry.ac import views

autocomplete_patterns = [
    path('buch/', views.ACBuchband.as_view(), name='acbuchband'),
    path('ausgabe/', views.ACAusgabe.as_view(), name='acausgabe'),
    path('band/', views.ACBand.as_view(), name='acband'),
    path('band/<str:create_field>/', views.ACBand.as_view(), name='acband'),
    path('musiker/', views.ACMusiker.as_view(), name='acmusiker'),
    path('musiker/<str:create_field>/', views.ACMusiker.as_view(), name='acmusiker'),
    path('veranstaltung/', views.ACVeranstaltung.as_view(), name='acveranstaltung'),
    path('gnd/', views.GND.as_view(), name='gnd'),
    # TODO: enable the lagerort autocomplete URL (see views.ACLagerort for more details)
    # path('lagerort/', views.ACLagerort.as_view(), name='aclagerort'),
]

urlpatterns = [
    path('', include(autocomplete_patterns)),
    path(
        '<str:model_name>/<str:create_field>/',
        views.ACBase.as_view(), name='accapture'
    ),
    # ACCreatable has a more involved object creation process and
    # gets the create_field directly from the model.
    path('<str:model_name>/', views.ACCreatable.as_view(), name='accapture'),
]
