from dbentry import models as _models
from dbentry.export import resources
from tests.case import DataTestCase
from tests.model_factory import make


class ResourceTestMethodsMixin:
    def test(self: "ResourceTestCase"):
        self.maxDiff = None
        dataset = self.resource.export()
        self.assertDictEqual(dataset.dict[0], self.expected_data)


class ResourceTestCase(DataTestCase):
    resource_class = None
    expected_data = None

    def setUp(self):
        self.test_objects = {
            _models.Artikel: self.artikel,
            _models.Audio: self.audio,
            _models.Brochure: self.brochure,
            _models.Buch: self.buch,
            _models.Foto: self.foto,
            _models.Plakat: self.plakat,
            _models.Kalender: self.kalender,
            _models.Video: self.video,
            _models.Katalog: self.katalog,
            _models.Ausgabe: self.ausgabe,
            _models.Band: self.band,
            _models.Musiker: self.musiker,
        }
        self.resource = self.resource_class()
        pk_key = "ID"
        if self.resource._meta.model in (_models.Brochure, _models.Katalog, _models.Kalender):
            # As always, these three models need special treatment.
            pk_key = "Id"
        self.expected_data[pk_key] = str(self.test_objects[self.resource._meta.model].pk)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bestand = make(_models.Bestand, lagerort__ort="Keller")
        cls.magazin = make(_models.Magazin, magazin_name="Testmagazin")
        cls.ausgabe = make(
            _models.Ausgabe,
            magazin=cls.magazin,
            ausgabejahr__jahr="2022",
            ausgabenum__num="2",
            ausgabemonat__monat__monat=["Mai", "Juni"],
            bestand=cls.bestand,
        )
        cls.land = make(_models.Land, land_name="Deutschland", code="DE")
        cls.bundesland = make(_models.Bundesland, bland_name="Nordrhein-Westfalen", code="NRW", land=cls.land)
        cls.ort = make(_models.Ort, stadt="Dortmund", land=cls.land, bland=cls.bundesland)
        cls.person = make(_models.Person, vorname="Alice", nachname="Tester")
        cls.autor = make(_models.Autor, person=cls.person)
        cls.genre = make(_models.Genre, genre="Testmusik")
        cls.schlagwort = make(_models.Schlagwort, schlagwort="Testobjekt")
        cls.musiker = make(
            _models.Musiker,
            kuenstler_name="Singer Alice",
            genre=cls.genre,
            musikeralias__alias=["Just Alice", "Bingo"],
            orte=cls.ort,
        )
        cls.band = make(
            _models.Band,
            band_name="Bob and Alice Band",
            genre=cls.genre,
            musiker=cls.musiker,
            bandalias__alias=["BAAB", "B.A.A.B."],
            orte=cls.ort,
        )
        cls.musiker.band_set.add(cls.band)
        cls.spielort = make(_models.Spielort, name="Westfalenhallen", ort=cls.ort)
        cls.veranstaltung = make(
            _models.Veranstaltung, name="Alice's Big Concert", datum="2022-02-02", spielort=cls.spielort
        )

        cls.artikel = make(
            _models.Artikel,
            schlagzeile="Schlagzeile",
            seite=15,
            seitenumfang="f",
            zusammenfassung="Ein Bericht über das Schreiben von Tests",
            ausgabe=cls.ausgabe,
            autor=cls.autor,
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
        )
        cls.audio = make(
            _models.Audio,
            titel="Titel",
            tracks=15,
            laufzeit="00:32:04",
            jahr="2022",
            land_pressung=cls.land,
            quelle="Live",
            original=True,
            plattennummer="123457-A",
            medium=make(_models.AudioMedium, medium="CD"),
            medium_qty=2,
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
            plattenfirma=make(_models.Plattenfirma, name="Supercool Records"),
            bestand=cls.bestand,
            beschreibung="Beschreibung",
        )
        cls.brochure = make(
            _models.Brochure,
            titel="Testbroschüre",
            zusammenfassung="Zusammenfassung",
            ausgabe=cls.ausgabe,
            jahre__jahr=["2022", "2023"],
            genre=cls.genre,
            schlagwort=cls.schlagwort,
            bestand=cls.bestand,
            beschreibung="Beschreibung",
        )
        cls.buch = make(
            _models.Buch,
            titel="Testbuch",
            seitenumfang=232,
            jahr="2022",
            auflage="1. Edition",
            schriftenreihe=make(_models.Schriftenreihe, name="Testreihe"),
            ISBN="9780471117094",
            sprache="deutsch",
            autor=cls.autor,
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
            herausgeber=make(_models.Herausgeber, herausgeber="Herausgeber"),
            verlag=make(_models.Verlag, verlag_name="Verlag"),
            bestand=cls.bestand,
        )
        cls.foto = make(
            _models.Foto,
            titel="Testfoto",
            size="DIN-A5",
            datum="2022",
            typ=_models.Foto.Types.POLAROID,
            farbe=True,
            owner="Charlie",
            reihe=make(_models.Bildreihe, name="Fotoreihe"),
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
            bestand=cls.bestand,
        )
        cls.plakat = make(
            _models.Plakat,
            titel="Testplakat",
            signatur="DINA3-11111",
            size="DIN-A3",
            datum="2022",
            reihe=make(_models.Bildreihe, name="Plakatreihe"),
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
            bestand=cls.bestand,
        )
        cls.kalender = make(
            _models.Kalender,
            titel="Testprogrammheft",
            zusammenfassung="Zusammenfassung",
            ausgabe=cls.ausgabe,
            jahre__jahr=["2022", "2023"],
            genre=cls.genre,
            bestand=cls.bestand,
            beschreibung="Beschreibung",
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
        )
        cls.video = make(
            _models.Video,
            titel="Testvideo",
            laufzeit="01:23:45",
            jahr="2022",
            quelle="Fernsehen",
            original=False,
            medium=make(_models.VideoMedium, medium="DVD"),
            medium_qty=3,
            musiker=cls.musiker,
            band=cls.band,
            schlagwort=cls.schlagwort,
            genre=cls.genre,
            ort=cls.ort,
            spielort=cls.spielort,
            veranstaltung=cls.veranstaltung,
            person=cls.person,
            bestand=cls.bestand,
        )
        cls.katalog = make(
            _models.Katalog,
            titel="Testkatalog",
            zusammenfassung="Zusammenfassung",
            art=_models.Katalog.Types.MERCH,
            ausgabe=cls.ausgabe,
            jahre__jahr=["2022", "2023"],
            genre=cls.genre,
            bestand=cls.bestand,
            beschreibung="Beschreibung",
        )

        cls.ausgabe.audio.add(cls.audio)


class TestArtikelResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.ArtikelResource
    expected_data = {
        "Magazin": "Testmagazin",
        "Ausgabe": "2022-02",
        "Schlagzeile": "Schlagzeile",
        "Seite": "15",
        "Seitenumfang": "f",
        "Zusammenfassung": "Ein Bericht über das Schreiben von Tests",
        "Autoren": "Alice Tester (AT)",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestAudioResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.AudioResource
    expected_data = {
        "Titel": "Titel",
        "Laufzeit": "0:32:04",
        "Anz. Tracks": "15",
        "Jahr": "2022",
        "Land Pressung": "Deutschland",
        "Plattennummer": "123457-A",
        "Quelle": "Live",
        "Originalmaterial": "Ja",
        "Speichermedium": "CD",
        "Anzahl": "2",
        "Link discogs.com": "",
        "Release ID (discogs)": "",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Plattenfirmen": "Supercool Records",
        "Ausgaben": "2022-02",
        "Bestände": "Keller",
        "Beschreibung": "Beschreibung",
    }


class TestAusgabeResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.AusgabeResource
    expected_data = {
        "Magazin": "Testmagazin",
        "Sonderausgabe": "Nein",
        "Erscheinungsdatum": "",
        "Jahrgang": "",
        "Ausgabennummern": "2",
        "Monate": "Jun, Mai",
        "Laufende Nummer": "-",
        "erschienen im Jahr": "2022",
        "Audio Materialien": "Titel",
        "Video Materialien": "-",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestBrochureResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.BrochureResource
    expected_data = {
        "Titel": "Testbroschüre",
        "Zusammenfassung": "Zusammenfassung",
        "Magazin": "Testmagazin",
        "Ausgabe": "2022-02",
        "Weblinks": "-",
        "Jahre": "2022, 2023",
        "Genres": "Testmusik",
        "Schlagwörter": "Testobjekt",
        "Bestände": "-",
        "Beschreibung": "Beschreibung",
    }


class TestBuchResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.BuchResource
    expected_data = {
        "Titel": "Testbuch",
        "Seitenumfang": "232",
        "Jahr": "2022",
        "Auflage": "1. Edition",
        "Schriftenreihe": "Testreihe",
        "Sammelband": "",
        "Ist Sammelband": "Nein",
        "ISBN": "9780471117094",
        "EAN": "",
        "Sprache": "deutsch",
        "Titel (Original)": "",
        "Jahr (Original)": "",
        "Autoren": "Alice Tester (AT)",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Herausgeber": "Herausgeber",
        "Verlage": "Verlag",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestFotoResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.FotoResource
    expected_data = {
        "Titel": "Testfoto",
        "Größe": "DIN-A5",
        "Art des Fotos": "polaroid",
        "Farbfoto": "Ja",
        "Zeitangabe": "2022",
        "Bildreihe": "Fotoreihe",
        "Rechteinhaber": "Charlie",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestPlakatResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.PlakatResource
    expected_data = {
        "Titel": "Testplakat",
        "Größe": "DIN-A3",
        "Zeitangabe": "2022",
        "Bildreihe": "Plakatreihe",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestKalenderResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.KalenderResource
    expected_data = {
        "Titel": "Testprogrammheft",
        "Zusammenfassung": "Zusammenfassung",
        "Magazin": "Testmagazin",
        "Ausgabe": "2022-02",
        "Weblinks": "-",
        "Jahre": "2022, 2023",
        "Genres": "Testmusik",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Bestände": "-",
        "Beschreibung": "Beschreibung",
    }


class TestVideoResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.VideoResource
    expected_data = {
        "Titel": "Testvideo",
        "Laufzeit": "1:23:45",
        "Jahr": "2022",
        "Originalmaterial": "Nein",
        "Quelle": "Fernsehen",
        "Speichermedium": "DVD",
        "Anzahl": "3",
        "Release ID (discogs)": "",
        "Link discogs.com": "",
        "Musiker": "Singer Alice",
        "Bands": "Bob and Alice Band",
        "Schlagwörter": "Testobjekt",
        "Genres": "Testmusik",
        "Orte": "Dortmund, DE-NRW",
        "Spielorte": "Westfalenhallen",
        "Veranstaltungen": "Alice's Big Concert",
        "Personen": "Alice Tester",
        "Ausgaben": "-",
        "Bestände": "Keller",
        "Beschreibung": "",
    }


class TestKatalogResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.KatalogResource
    expected_data = {
        "Titel": "Testkatalog",
        "Art d. Kataloges": "merch",
        "Zusammenfassung": "Zusammenfassung",
        "Magazin": "Testmagazin",
        "Ausgabe": "2022-02",
        "Weblinks": "-",
        "Jahre": "2022, 2023",
        "Genres": "Testmusik",
        "Bestände": "Keller",
        "Beschreibung": "Beschreibung",
    }


class TestBandResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.BandResource
    expected_data = {
        "Bandname": "Bob and Alice Band",
        "Weblinks": "-",
        "Genres": "Testmusik",
        "Alias": "B.A.A.B., BAAB",
        "Band-Mitglieder": "Singer Alice",
        "Assoziierte Orte": "Dortmund, DE-NRW",
        "Beschreibung": "",
    }


class TestMusikerResource(ResourceTestMethodsMixin, ResourceTestCase):
    resource_class = resources.MusikerResource
    expected_data = {
        "Künstlername": "Singer Alice",
        "Person": "",
        "Weblinks": "-",
        "Genres": "Testmusik",
        "Alias": "Bingo, Just Alice",
        "Bands (Mitglied)": "Bob and Alice Band",
        "Assoziierte Orte": "Dortmund, DE-NRW",
        "Instrumente": "-",
        "Beschreibung": "",
    }
