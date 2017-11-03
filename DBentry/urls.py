from django.conf.urls import url,  include

from .views import *

autocomplete_patterns = [
    url(r'^audio/$',        ACBase.as_view(model = audio, create_field = 'titel'),              name="acaudio"), 
    url(r'^ausgabe/$',      ACBase.as_view(model = ausgabe),                                    name = 'acausgabe'), 
    url(r'^autor/$',        ACBase.as_view(model = autor),                                      name = 'acautor'), 
    url(r'^band/$',         ACBase.as_view(model = band, create_field='band_name'),             name = 'acband'),
    url(r'^bildmaterial/$', ACBase.as_view(model = bildmaterial),                               name="acbildmaterial"),
    url(r'^bland/$',        ACBase.as_view(model = bundesland),                                 name = 'acbland'),
    url(r'^buch/$',         ACBase.as_view(model = buch),                                       name = 'acbuch'), 
    url(r'^buchserie/$',    ACBase.as_view(model = buch_serie, create_field = 'serie'),         name = 'acbuchserie'),
    url(r'^datei/$',        ACBase.as_view(model = datei),                                      name="acdatei"), 
    url(r'^dokument/$',     ACBase.as_view(model = dokument),                                   name="acdokument"),    
    url(r'^geber/$',        ACBase.as_view(model = geber, create_field = 'name'),               name = 'acgeber'), 
    url(r'^genre/$',        ACBase.as_view(model = genre, create_field='genre'),                name = 'acgenre'),
    url(r'^instrument/$',   ACBase.as_view(model = instrument,  create_field = 'instrument'),   name = 'acinstrument'),
    url(r'^lagerort/$',     ACBase.as_view(model = lagerort),                                   name = 'aclagerort'),  
    url(r'^land/$',         ACBase.as_view(model = land, create_field = 'land_name'),           name = 'acland'),
    url(r'^magazin/$',      ACBase.as_view(model = magazin,  create_field = 'magazin_name'),    name = 'acmagazin'),
    url(r'^memorabilien/$', ACBase.as_view(model = memorabilien),                               name="acmemorabilien"), 
    url(r'^musiker/$',      ACBase.as_view(model = musiker, create_field = 'kuenstler_name'),   name = 'acmusiker'),
    url(r'^ort/$',          ACBase.as_view(model = ort),                                        name = 'acort'), 
    url(r'^person/$',       ACBase.as_view(model = person),                                     name = 'acperson'), 
    url(r'^prov/$',         ACProv.as_view(model = provenienz),                                 name = 'acprov'),  
    url(r'^schlagwort/$',   ACBase.as_view(model = schlagwort, create_field = 'schlagwort'),    name = 'acschlagwort'),
    url(r'^sender/$',       ACBase.as_view(model = sender,  create_field = 'name'),             name = 'acsender'), 
    url(r'^spielort/$',     ACBase.as_view(model = spielort),                                   name = 'acspielort'), 
    url(r'^sprache/$',      ACBase.as_view(model = sprache),                                    name = 'acsprache'),
    url(r'^veranstaltung/$',ACBase.as_view(model = veranstaltung),                              name = 'acveranstaltung'), 
    url(r'^verlag/$',       ACBase.as_view(model = verlag, create_field='verlag_name'),         name = 'acverlag'), 
    url(r'video/$',         ACBase.as_view(model = video),                                      name="acvideo"), 
]

# A place for the evil twins of the previous ac patterns that want to create objects although they are not allowed to
# (on advanced search forms)
autocomplete_patterns_nocreate = [
    url(r'^band_nocreate/$',            ACBase.as_view(model = band),                           name = 'acband_nocreate'),
    url(r'^genre_nocreate/$',           ACBase.as_view(model = genre),                          name = 'acgenre_nocreate'), 
    url(r'^instrument_nocreate/$',      ACBase.as_view(model = instrument),                     name = 'acinstrument_nocreate'),
    url(r'^magazin_nocreate/$',         ACBase.as_view(model = magazin),                        name = 'acmagazin_nocreate'),
    url(r'^musiker_nocreate/$',         ACBase.as_view(model = musiker),                        name = 'acmusiker_nocreate'),
    url(r'^land_nocreate/$',            ACBase.as_view(model = land),                           name = 'acland_nocreate'),
    url(r'^schlagwort_nocreate/$',      ACBase.as_view(model = schlagwort),                     name = 'acschlagwort_nocreate'),
]

wip = [ 
    url(r'^format_typ/$',   ACBase.as_view(model=FormatTyp, create_field = 'typ'),              name="acformat_typ"), 
    url(r'^format_size/$',  ACBase.as_view(model=FormatSize, create_field = 'size'),            name="acformat_size"),
    url(r'^noise_red/$',    ACBase.as_view(model=NoiseRed, create_field='verfahren'),           name="acnoisered"),  
    url(r'^label/$',        ACBase.as_view(model=plattenfirma, create_field='name'),            name="aclabel"), 
]

autocomplete_patterns += wip

urlpatterns = [
    url(r'ac/', include(autocomplete_patterns)),
    url(r'ac/', include(autocomplete_patterns_nocreate))
]

admin_tools_urls = [
    url(r'^bulk_ausgabe/$', BulkAusgabe.as_view(), name='bulk_ausgabe'), 
]
