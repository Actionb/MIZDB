from .registry import register
from .helptext import ModelAdminHelpText

from DBentry.models import *
from DBentry.admin import *
    

class MIZModelAdminHelpText(ModelAdminHelpText):
    
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
class ArtikelHelpText(MIZModelAdminHelpText):
    model = artikel

#@register()
class AudioHelpText(MIZModelAdminHelpText):
    model = audio
    
@register()
class AusgabeHelpText(MIZModelAdminHelpText):
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
class AusgabeJahrHelpText(MIZModelAdminHelpText):
    model = ausgabe_jahr

#@register()
class AusgabeLnumHelpText(MIZModelAdminHelpText):
    model = ausgabe_lnum

#@register()
class AusgabeMonatHelpText(MIZModelAdminHelpText):
    model = ausgabe_monat

#@register()
class AusgabeNumHelpText(MIZModelAdminHelpText):
    model = ausgabe_num

#@register()
class AutorHelpText(MIZModelAdminHelpText):
    model = autor

#@register()
class BandHelpText(MIZModelAdminHelpText):
    model = band

#@register()
class BandAliasHelpText(MIZModelAdminHelpText):
    model = band_alias
    
@register()
class BestandHelpText(ModelAdminHelpText):
    
    model = bestand
    
    inline_text = 'Hier kann das Objekt im Bestand des Archives registriert werden. Dazu ist eine Angabe des Lagerortes des Objektes erforderlich. \nDazu kann auch noch die Provenienz (Herkunft, Ursprung) des Objektes angegeben werden.'

#@register()
class BildmaterialHelpText(MIZModelAdminHelpText):
    model = bildmaterial

#@register()
class BuchHelpText(MIZModelAdminHelpText):
    model = buch

#@register()
class BundeslandHelpText(MIZModelAdminHelpText):
    model = bundesland

#@register()
class DateiHelpText(MIZModelAdminHelpText):
    model = datei

#@register()
class DokumentHelpText(MIZModelAdminHelpText):
    model = dokument

#@register()
class FormatHelpText(MIZModelAdminHelpText):
    model = Format

#@register()
class FormatsizeHelpText(MIZModelAdminHelpText):
    model = FormatSize

#@register()
class FormattagHelpText(MIZModelAdminHelpText):
    model = FormatTag

#@register()
class FormattypHelpText(MIZModelAdminHelpText):
    model = FormatTyp

#@register()
class GeberHelpText(MIZModelAdminHelpText):
    model = geber
    
#@register()
class GenreHelpText(MIZModelAdminHelpText):
    
    model = genre
    
    inline_text = """
        Genres der ausgewählten Musiker oder Bands müssen hier nicht noch einmal explizit ausgewählt werden.
    """

#@register()
class GenreAliasHelpText(MIZModelAdminHelpText):
    model = genre_alias

#@register()
class HerausgeberHelpText(MIZModelAdminHelpText):
    model = Herausgeber

#@register()
class InstrumentHelpText(MIZModelAdminHelpText):
    model = instrument

#@register()
class InstrumentAliasHelpText(MIZModelAdminHelpText):
    model = instrument_alias

#@register()
class KreisHelpText(MIZModelAdminHelpText):
    model = kreis

#@register()
class LagerortHelpText(MIZModelAdminHelpText):
    model = lagerort

#@register()
class LandHelpText(MIZModelAdminHelpText):
    model = land

#@register()
class LandAliasHelpText(MIZModelAdminHelpText):
    model = land_alias

#@register()
class MagazinHelpText(MIZModelAdminHelpText):
    model = magazin

#@register()
class MemorabilienHelpText(MIZModelAdminHelpText):
    model = memorabilien

#@register()
class MonatHelpText(MIZModelAdminHelpText):
    model = monat

#@register()
class MusikerHelpText(MIZModelAdminHelpText):
    model = musiker

#@register()
class MusikerAliasHelpText(MIZModelAdminHelpText):
    model = musiker_alias

#@register()
class NoiseredHelpText(MIZModelAdminHelpText):
    model = NoiseRed

#@register()
class OrganisationHelpText(MIZModelAdminHelpText):
    model = Organisation

#@register()
class OrtHelpText(MIZModelAdminHelpText):
    model = ort

#@register()
class PersonHelpText(MIZModelAdminHelpText):
    model = person

#@register()
class PlattenfirmaHelpText(MIZModelAdminHelpText):
    model = plattenfirma

#@register()
class ProvenienzHelpText(MIZModelAdminHelpText):
    model = provenienz

#@register()
class SchlagwortHelpText(MIZModelAdminHelpText):
    model = schlagwort

#@register()
class SchlagwortAliasHelpText(MIZModelAdminHelpText):
    model = schlagwort_alias

#@register()
class SchriftenreiheHelpText(MIZModelAdminHelpText):
    model = schriftenreihe

#@register()
class SenderHelpText(MIZModelAdminHelpText):
    model = sender

#@register()
class SenderAliasHelpText(MIZModelAdminHelpText):
    model = sender_alias

#@register()
class SpielortHelpText(MIZModelAdminHelpText):
    model = spielort

#@register()
class SpielortAliasHelpText(MIZModelAdminHelpText):
    model = spielort_alias

#@register()
class SpracheHelpText(MIZModelAdminHelpText):
    model = sprache

#@register()
class TechnikHelpText(MIZModelAdminHelpText):
    model = technik

#@register()
class VeranstaltungHelpText(MIZModelAdminHelpText):
    model = veranstaltung

#@register()
class VeranstaltungAliasHelpText(MIZModelAdminHelpText):
    model = veranstaltung_alias

#@register()
class VerlagHelpText(MIZModelAdminHelpText):
    model = verlag

#@register()
class VideoHelpText(MIZModelAdminHelpText):
    model = video
