from .registry import register
from .helptext import ModelHelpText

from DBentry.models import *
from DBentry.admin import *
    

class MIZModelHelpText(ModelHelpText):
    
    help_items = [('description', 'Beschreibung'), ('fields', 'Felder'), ('inlines', 'Inlines'), ('examples', 'Beispiele')]
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'beschreibung' not in self.fields and 'beschreibung' in self.get_form().base_fields:
            self.fields['beschreibung'] = "Hier können etwaige Anmerkungen bezüglich dieses Objektes, die dem Kunden behilflich sein könnten, notiert werden."
        if 'bemerkungen' not in self.fields and 'bemerkungen' in self.get_form().base_fields:
            self.fields['bemerkungen'] =  """
                In dieses Feld können Kommentare für Archiv-Mitarbeiter eingetragen werden. Zum Beispiel könnte ein Mitarbeiter eine Erinnerungsnotiz hinterlassen oder Besonderheiten, die für die Bearbeitung dieses Objektes hilfreich sein könnten, vermerken.
                Dieses Feld wird einem Kunden NICHT angezeigt.
            """

#@register()
class ArtikelHelpText(MIZModelHelpText):
    model = artikel

#@register()
class AudioHelpText(MIZModelHelpText):
    model = audio
    
#@register()
class AusgabeHelpText(MIZModelHelpText):
    help_items = [('description', 'Beschreibung'), ('fields', 'Felder'), ('inlines', 'Inlines'), ('notes', 'Bemerkung'), ('text', 'Textliche Darstellung')]
    
    model = ausgabe
    
    description = """
        Die volle Korrektheit aller Angaben zu gewährleisten, ist in vielen Fällen nur begrenzt möglich, da für Begriffe wie 'Jahrgang', 'laufende Nummer' oder 'Ausgabennummer' """ + \
        """ keine Standardisierung vorliegt und diese daher von Magazin zu Magazin - und sogar von Ausgabe zu Ausgabe - unterschiedlich gehandhabt werden.
    """
    
    fields = {
        'status': "Wählen Sie hier den Bearbeitungsstatus im Bezug auf die Erfassung der Artikel dieser Ausgabe.", 
        'sonderausgabe': "Sonderausgaben fehlen gelegentlich numerische Angaben.", 
        'e_datum': "Oft ist diese Angabe in der vorangegangenen Ausgabe zu finden. Erlaubte Formate sind 'tt.mm.jjjj' (31.12.1999) oder 'jjjj-mm-tt' (1999-12-31).", 
        'jahrgang': "Ist auf dem Titelblatt oder in dem Impressum ein Jahrgang vermerkt, so kann dieser hier eingetragen werden. Im Englischen ist dafür der Begriff 'Volume' geläufig.", 
    }
    
    inlines = {
        'Ausgabennummer': "Neben der Jahresangabe ist auf dem Titelblatt oft auch eine weiter Nummer zu finden, welche entweder die Ausgabennummer oder die laufende Nummer darstellt.\n" + \
        "Die Ausgabennummer beschreibt die 'x-te' Ausgabe in einem Jahr, was bedeutet, dass - im Gegensatz zur laufenden Nummer - die Zählung bei einem neuen Jahr/Jahrgang erneut bei 1 beginnt. \n" + \
        "Häufig kommt diese Nummer auch als Zusatz im Strichcode der Ausgabe vor.",  
        
        'Monate': "Die Monate, die dieser Ausgabe angehören. Sind keine Monate ausdrücklich (z.B. 'Jan/Feb-2002') erwähnt und ist es weiterhin nicht erkenntlich, dass sich Zahlenangaben auf Monate beziehen, sollte davon abgesehn werden, Monate einzutragen.\n" + \
        "Findet man z.B. Angaben in der Form '12-2001' zu der Ausgabe, ist damit nicht unweigerlich der Monat Dezember gemeint!", 
        
        'Laufende Nummer': "Die fortlaufende Nummer in der Gesamtheit aller erschienen Ausgaben dieses Magazines.", 
        
        'Jahre': 'Selbsterklärend. Bitte vier-stellige Jahreszahlen verwenden.', 
        
        'Musik-Beilagen': 'Liegen der Ausgabe Musik-Medien bei, so können diese hier eingetragen werden. Näheres finden sie unter der <a href="/admin/help/audio/" target="_blank">Audio-Hilfe</a>.', 
    }
    
    notes = """
        Zu der Ausgabennummer und der laufenden Nummer: wichtig ist, dass man anhand der Angaben in der Datenbank die dazu passende Ausgabe im Lager finden kann.
    """
    
    text = """
    Die textliche Darstellung...
    """
    
#@register()
class AusgabeJahrHelpText(MIZModelHelpText):
    model = ausgabe_jahr

#@register()
class AusgabeLnumHelpText(MIZModelHelpText):
    model = ausgabe_lnum

#@register()
class AusgabeMonatHelpText(MIZModelHelpText):
    model = ausgabe_monat

#@register()
class AusgabeNumHelpText(MIZModelHelpText):
    model = ausgabe_num

#@register()
class AutorHelpText(MIZModelHelpText):
    model = autor

#@register()
class BandHelpText(MIZModelHelpText):
    model = band

#@register()
class BandAliasHelpText(MIZModelHelpText):
    model = band_alias
    
#@register()
class BestandHelpText(ModelHelpText):
    
    model = bestand
    
    inline_text = 'Hier kann das Objekt im Bestand des Archives registriert werden. Dazu ist eine Angabe des Lagerortes des Objektes erforderlich. \nDazu kann auch noch die Provenienz (Herkunft, Ursprung) des Objektes angegeben werden.'

#@register()
class BildmaterialHelpText(MIZModelHelpText):
    model = bildmaterial

#@register()
class BuchHelpText(MIZModelHelpText):
    model = buch

#@register()
class BundeslandHelpText(MIZModelHelpText):
    model = bundesland

#@register()
class DateiHelpText(MIZModelHelpText):
    model = datei

#@register()
class DokumentHelpText(MIZModelHelpText):
    model = dokument

#@register()
class FormatHelpText(MIZModelHelpText):
    model = Format

#@register()
class FormatsizeHelpText(MIZModelHelpText):
    model = FormatSize

#@register()
class FormattagHelpText(MIZModelHelpText):
    model = FormatTag

#@register()
class FormattypHelpText(MIZModelHelpText):
    model = FormatTyp

#@register()
class GeberHelpText(MIZModelHelpText):
    model = geber
    
#@register()
class GenreHelpText(MIZModelHelpText):
    
    model = genre
    
    inline_text = """
        Genres der ausgewählten Musiker oder Bands müssen hier nicht noch einmal explizit ausgewählt werden.
    """

#@register()
class GenreAliasHelpText(MIZModelHelpText):
    model = genre_alias

#@register()
class HerausgeberHelpText(MIZModelHelpText):
    model = Herausgeber

#@register()
class InstrumentHelpText(MIZModelHelpText):
    model = instrument

#@register()
class InstrumentAliasHelpText(MIZModelHelpText):
    model = instrument_alias

#@register()
class KreisHelpText(MIZModelHelpText):
    model = kreis

#@register()
class LagerortHelpText(MIZModelHelpText):
    model = lagerort

#@register()
class LandHelpText(MIZModelHelpText):
    model = land

#@register()
class LandAliasHelpText(MIZModelHelpText):
    model = land_alias

#@register()
class MagazinHelpText(MIZModelHelpText):
    model = magazin

#@register()
class MemorabilienHelpText(MIZModelHelpText):
    model = memorabilien

#@register()
class MonatHelpText(MIZModelHelpText):
    model = monat

#@register()
class MusikerHelpText(MIZModelHelpText):
    model = musiker

#@register()
class MusikerAliasHelpText(MIZModelHelpText):
    model = musiker_alias

#@register()
class NoiseredHelpText(MIZModelHelpText):
    model = NoiseRed

#@register()
class OrganisationHelpText(MIZModelHelpText):
    model = Organisation

#@register()
class OrtHelpText(MIZModelHelpText):
    model = ort

#@register()
class PersonHelpText(MIZModelHelpText):
    model = person

#@register()
class PlattenfirmaHelpText(MIZModelHelpText):
    model = plattenfirma

#@register()
class ProvenienzHelpText(MIZModelHelpText):
    model = provenienz

#@register()
class SchlagwortHelpText(MIZModelHelpText):
    model = schlagwort

#@register()
class SchlagwortAliasHelpText(MIZModelHelpText):
    model = schlagwort_alias

#@register()
class SchriftenreiheHelpText(MIZModelHelpText):
    model = schriftenreihe

#@register()
class SenderHelpText(MIZModelHelpText):
    model = sender

#@register()
class SenderAliasHelpText(MIZModelHelpText):
    model = sender_alias

#@register()
class SpielortHelpText(MIZModelHelpText):
    model = spielort

#@register()
class SpielortAliasHelpText(MIZModelHelpText):
    model = spielort_alias

#@register()
class SpracheHelpText(MIZModelHelpText):
    model = sprache

#@register()
class TechnikHelpText(MIZModelHelpText):
    model = technik

#@register()
class VeranstaltungHelpText(MIZModelHelpText):
    model = veranstaltung

#@register()
class VeranstaltungAliasHelpText(MIZModelHelpText):
    model = veranstaltung_alias

#@register()
class VerlagHelpText(MIZModelHelpText):
    model = verlag

#@register()
class VideoHelpText(MIZModelHelpText):
    model = video
