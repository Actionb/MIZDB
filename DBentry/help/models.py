from .registry import register
from .helptext import ModelHelpText

from DBentry.models import *
from DBentry.admin import *
    

@register()
class ArtikelHelpText(ModelHelpText):
    
    model = artikel
    admin_model_class = ArtikelAdmin
    
    description = """
        Die Hilfe für das Modell Artikel.
    """
    
    details = """
        So viele Details!
    """
    
    details = {
        'description': 'Detailed description that is super very extremly was there an e missing long and just for testing purposes maybe you should try to use lore ipsum what its face considering you have no idea what you are doing?', 
        'fields' : ['beep boop']
    }
    
    details = [
        {'label':'description', 'text':'Detailed description that is super very extremly was there an e missing long and just for testing purposes maybe you should try to use lore ipsum what its face considering you have no idea what you are doing?'}, 
        'beep boop'
    ]
    
    examples = """
        Mach ne Schlagzeile.
    """
    
    fields = {
        'schlagzeile' : 'Beep boop', 
        'ausgabe' : 'Wählen Sie die Ausgabe.'
    }
#    
#    ausgabe__magazin = "Wählen Sie hier das Magazin des Artikels."
#    ausgabe = "Wählen Sie die Ausgabe."
    
    notes = """
        Notes go here
    """
    
@register()
class GenreHelpText(ModelHelpText):
    
    model = genre
    
    inline_text = """
        Genres der ausgewählten Musiker oder Bands müssen hier nicht noch einmal explizit ausgewählt werden.
    """
    
#    @classmethod
#    def as_inline(cls, request, form = None):
#        return "Bei der Auswahl der Genres m"

    
@register()
class AusgabeHelpText(ModelHelpText):
    
    model = ausgabe
    
    fields = {
     'magazin': "Wählen Sie hier das Magazin."
    }
    
@register()
class MagazinHelpText(ModelHelpText):
    
    model = magazin
    
    magazin_name = "Der Name des Magazines."
    
@register()
class BuchHelpText(ModelHelpText):
    
    model = buch
    
@register()
class DateiHelpText(ModelHelpText):
    
    model = datei
