from django.urls import include, path

from .views import ACAusgabe, ACBase, ACBuchband, ACCreatable, GND

autocomplete_patterns = [
    path('buch/', ACBuchband.as_view(), name='acbuchband'),
    path('ausgabe/', ACAusgabe.as_view(), name='acausgabe'),
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
