from DBentry.bulk.views import BulkAusgabe
from DBentry.bulk.forms import BulkFormAusgabe
from DBentry.help.registry import register
from DBentry.help.helptext import FormViewHelpText

@register(url_name='help_bulk_ausgabe')
class BulkFormHelpText(FormViewHelpText):
    
    site_title = 'Hilfe für Ausgaben Erstellung'
    breadcrumbs_title = 'Ausgaben Erstellung'
    
    form_class = BulkFormAusgabe
    target_view_class = BulkAusgabe
    
    index_title = 'Ausgaben Erstellung'
    help_items = ['beschreibung', ('erlaubte_zeichen', 'Erlaubte Zeichen'), 'beispiele']
    
    fields = {
    }
    
    beschreibung =  """
        Dieses Formular dient zur schnellen Eingabe vieler Ausgaben.
        Dabei gilt die Regel, dass allen Ausgaben dasselbe Jahr und derselbe Jahrgang zugewiesen werden. Es ist also nicht möglich, mehrere 'Jahrgänge' auf einmal einzugeben.
        Liegt allen Ausgaben eine Musik-CD, o.ä. bei, setze den Haken bei dem Feld 'Musik-Beilage'. Ein Datensatz entsprechend dem Titel "Musik-Beilage: <Name des Magazins> <Name der Ausgabe>" wird dann in der Audiotabelle erstellt und mit der jeweiligen Ausgabe verknüpft.
        
        Mit den Auswahlfeldern zu Lagerort und Dublettenlagerort kann festgelegt werden, wo diese Ausgaben (und eventuelle Dubletten) gelagert werden.
        Sollte eine der im Formular angegebenen Ausgaben bereits einen Bestand in der Datenbank haben, so wird automatisch ein Dublettenbestand hinzugefügt und die vorhandene Ausgabe erscheint im Vorschau-Bereich 'Bereits vorhanden'. Bitte kontrolliert die Korrektheit eurer Angaben, sollte dies der Fall sein.
        
        Monate bitte als Nummern angeben und Leerzeichen vermeiden!
        
        In der Vorschau könnt ihr die resultierenden Ausgaben eurer Angaben überprüfen.
        <span style="color:red;">WICHTIG</span>: Es wird abgespeichert was in dem Formular steht, nicht was in der Vorschau gezeigt wird! Erstellt ihr eine Vorschau zu einer Reihe von Angaben und ändert dann die Angaben wieder, werden die gespeicherten Ausgaben NICHT der Vorschau entsprechen.
        Es ist also am besten, immer erst eine Vorschau nach jeder Änderung zu erstellen und danach abzuspeichern!
                    
        """

    erlaubte_zeichen = [
        {'label':' "," (Trennzeichen)', 'text':'Ein Komma trennt einzelne Gruppierungen von Angaben voneinander: 1,3,6-8 = 1,3,6,7,8'}, 
        {'label':' "-" (von bis)', 'text':'Das Minus-Zeichen stellt eine Reihe von Angaben dar: 1-4 = 1,2,3,4'}, 
        {'label':' "/" (einfache Gruppierung)', 'text':'Das Slash-Zeichen weist einer einzelnen Ausgabe mehrere Angaben zu: 1,3,6/7 = 1,3,6 UND 7'}, 
        {'label':' "*" (mehrfache Gruppierung)', 'text':'Das Sternchen erlaubt Zuweisung mehrerer Angaben zu einer Reihe (Kombination von "-" und "/"): 1-4*2 = 1/2, 3/4 oder 1-6*3 = 1/2/3, 4/5/6'}, 
        
    ]
    
    beispiele = """
        Eine Ausgabe mit der Nummer 6 und den Monaten April und Mai:
        Nummer-Feld: 6
        Monat-Feld: 4/5
        
        Zwei Ausgaben mit den laufenden Nummern 253 und 255:
        Laufende Nummer: 253, 255
        
        Drei Ausgaben mit Nummern 3 bis 5 und Monaten Januar/Februar und März/April und Mai/Juni:
        Nummer: 3-5 (oder natürlich auch 3,4,5)
        Monat: 1-6*2 (oder auch 1/2, 3/4, 5/6)
        
        Ein ganzer Jahrgang von 11 Ausgaben mit Monaten Jan bis Dez, wobei im Juli und August eine zwei-monatige Ausgabe erschienen ist:
        Monat: 1-6, 7/8, 9-12 (oder auch 1,2,3,4,5,6,7/8,9,10,11,12)
        
        Eine jahresübergreifende Ausgabe mit dem Monat Dezember im Jahre 2000 und dem Monat Januar im Jahre 2001:
        Jahr: 2000,2001 (oder 2000/2001)
        Monat: 12/1
        """
