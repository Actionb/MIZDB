Person
======


Datensätze, die (natürliche) Personen repräsentieren.



Zur Verdeutlichung: einem
 [Musiker](musiker.md "Musiker") (mit eventuellem Künstlernamen) lässt sich eine Person mit Realnamen zuordnen. So entspricht die
 *Person* mit dem Namen **Sir Richard Starkey** dem *Musiker* mit dem Namen
 **[Ringo Starr](https://en.wikipedia.org/wiki/de:Ringo_Starr "wikipedia:de:Ringo Starr")**.



## Felder { .fs-3 }


### Vorname { .fs-5 }



Vorname(n) des
 [bürgerlichen Namens](https://en.wikipedia.org/wiki/de:Realname#B.C3.BCrgerlicher_Name "wikipedia:de:Realname") der Person.
 

### Nachname { .fs-5 }



Nachname(n) des bürgerlichen Namens der Person.

### Normdatei ID { .fs-5 }



Mit diesem
 [Kombinationsfeld](bedienelement.md#Kombinationsfeld.2FCombobox "Bedienelement") kann die
 [gemeinsame Normdatei (GND)](#Gemeinsame_Normdatei) der deutschen Nationalbibliothek (DNB) durchsucht werden.
 
Ihr gebt den vollständigen Namen der Person ein und wählt anschließend den passenden Eintrag aus der Auswahlliste aus. Die Normdatei ID wird zwischen den Klammern angezeigt.

### Link DNB { .fs-5 }



Link zum Eintrag zu dieser Person auf der Webseite der deutschen Nationalbibliothek.

### Beschreibung { .fs-5 }



Ein Feld für weitere Angaben, welche in kein anderes der Felder passen.

### Bemerkungen { .fs-5 }



Notizen für Archiv-Mitarbeiter. Nur Mitarbeiter können dieses Felder sehen.



---


### Assoziierte Orte { .fs-5 }




[Orte](ort.md "Ort"), mit denen die Person assoziiert ist oder war. Zum Beispiel Geburtsort oder Stadt, in der die Person tätig war.
 

### Gemeinsame Normdatei { .fs-5 }


Die
 [gemeinsame Normdatei (GND)](https://en.wikipedia.org/wiki/de:Gemeinsame_Normdatei "wikipedia:de:Gemeinsame Normdatei") ist ein Verzeichnis, in welcher Dinge wie Personennamen oder Körperschaften normalisiert wurden. Dadurch, dass sich Archive und Bibliotheken bei ihren Persondaten auf eine gemeinsame Normdatei beziehen, können Personendaten leichter getauscht und verglichen werden. Wenn ein Archiv in ihrem Datensatz für die Person "John Lennon" die Normdatei ID
 `118571575` angibt, dann ist es für andere Archive ersichtlich, dass damit John Lennon der Beatles gemeint ist:
 [John Lennon GND Eintrag](http://d-nb.info/gnd/118571575)



Zur Ermittlung dieser wichtigen ID stehen euch zwei Möglichkeiten zur Verfügung:



* eine direkte Suchanfrage mit Hilfe des Bedienelementes



Ihr gebt den Namen der Person ein und eine Liste von passenden Datensätzen aus der Datenbank der deutschen Nationalbibliothek wird angezeigt. Aus dieser Liste müsst ihr den richtigen Eintrag auswählen. Tätigt ihr eine Auswahl und speichert das Formular ab, dann wird automatisch in das untere Feld
 [Link DNB](#Link_DNB) ein Link zum Datensatz mit der ausgewählten ID eingefügt. Wenn die angezeigten Suchergebnisse nicht eindeutig genug sind (z.B. mehrere Einträge mit demselben Namen), müsst ihr auf der Seite der Nationalbibliothek nach der richtigen ID suchen.
 

* Suche auf der Seite der deutschen Nationalbibliothek



Um zum Suchformular der DNB zu gelangen, könnt ihr auch auf den Link im Hilfetext unter dem Feld
 [Link DNB](#Link_DNB) klicken (oder hier:
 [Klick!](https://portal.dnb.de/opac/checkCategory?categoryId=persons)). Die Suche sollte bereits auf Normdaten für Personen eingeschränkt sein (nachzuprüfen: Standorte/Kataloge ➤ Einschränken auf Normdaten: ➤ Häkchen bei Personen). Jetzt müsst ihr oben als Suchschlüssel "Alle Bereiche" ("Titel" sollte voreingestellt sein) auswählen und den Namen der Person rechts daneben eintragen. Die Suche kann dann durch Betätigen der Eingabetaste (Enter) oder durch einen Klick auf Finden durchgeführt werden. Anschließend müsst ihr die Ergebnisse nach dem passenden Eintrag durchsuchen. Habt ihr den richtigen gefunden, dann müsst ihr den Link, der neben "Link zu diesem Datensatz" angegeben ist, kopieren. Diesen fügt ihr dann im Personenformular in das Feld 'Link DNB' ein. Die Datenbank wird dann die ID aus diesem Link auslesen und abspeichern.
 

* Beispiel für eine uneindeutige Suche
* [![](/mediawiki/images/0/05/Extended_search_dnb.png)](datei:extended_search_dnb.png.md)



Erweiterte Suche der DNB
* [![](/mediawiki/images/9/9d/Dnb_gnd_link.png)](datei:dnb_gnd_link.png.md)



Ausschnitt mit dem Link zum Datensatz, den ihr kopieren müsst


### Weblinks { .fs-5 }


* [Deutsche Nationalbibliothek über die gemeinsame Normdatei](https://www.dnb.de/DE/Professionell/Standardisierung/GND/gnd_node.html)
* [Suchformular der deutschen Nationalbibliothek](https://portal.dnb.de/opac/checkCategory?categoryId=persons)
