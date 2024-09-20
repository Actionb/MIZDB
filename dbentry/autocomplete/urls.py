from django.urls import path

from dbentry.autocomplete.views import (
    AutocompleteAusgabe,
    AutocompleteAutor,
    AutocompleteBuchband,
    AutocompleteMagazin,
    AutocompleteMostUsed,
    AutocompletePerson,
    AutocompleteProvenienz,
    MIZAutocompleteView,
)

urlpatterns = [
    path("", MIZAutocompleteView.as_view(), name="autocomplete"),
    path("ausgabe/", AutocompleteAusgabe.as_view(), name="autocomplete_ausgabe"),
    path("autor/", AutocompleteAutor.as_view(), name="autocomplete_autor"),
    path("buchband/", AutocompleteBuchband.as_view(), name="autocomplete_buchband"),
    path("person/", AutocompletePerson.as_view(), name="autocomplete_person"),
    path("magazin/", AutocompleteMagazin.as_view(), name="autocomplete_magazin"),
    path("provenienz/", AutocompleteProvenienz.as_view(), name="autocomplete_provenienz"),
    path("schlagwort/", AutocompleteMostUsed.as_view(), name="autocomplete_schlagwort"),
    path("genre/", AutocompleteMostUsed.as_view(), name="autocomplete_genre"),
]
