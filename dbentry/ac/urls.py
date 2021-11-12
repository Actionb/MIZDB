from django.urls import include, path

from .views import ACAusgabe, ACBand, ACBase, ACBuchband, ACCreatable, ACMusiker, GND

autocomplete_patterns = [
    path('buch/', ACBuchband.as_view(), name='acbuchband'),
    path('ausgabe/', ACAusgabe.as_view(), name='acausgabe'),
    path('band/<str:create_field>/', ACBand.as_view(), name='acband'),
    path('musiker/<str:create_field>/', ACMusiker.as_view(), name='acmusiker'),
    path('gnd/', GND.as_view(), name='gnd')
]

urlpatterns = [
    path('', include(autocomplete_patterns)),
    path(
        '<str:model_name>/<str:create_field>/',
        ACBase.as_view(), name='accapture'
    ),
    # ACCreatable has a more involved object creation process and
    # gets the create_field directly from the model.
    path('<str:model_name>/', ACCreatable.as_view(), name='accapture'),
]
