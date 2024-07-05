Bedienelement
=============


Die Seiten und Formulare der Datenbank verwenden verschiedene
 [Steuer- oder Bedienelemente](https://en.wikipedia.org/wiki/de:Steuerelement "wikipedia:de:Steuerelement"), deren Funktionsweisen hier kurz erklärt wird.



### Einfache Felder


### Textfeld { .fs-5 }



Ein Element, dass jede Form von Text bis zu einer bestimmten Länge (meist 200 Zeichen) annimmt. Die Größe des Elements und die erlaubte Länge des Textes stehen in keinem Zusammenhang.


### Textfeld mit variabler Grösse { .fs-5 }



Ein Textfeld, das praktisch unbegrenzt ist, was die Länge des Textes betrifft. Wenn man auf das Symbol in der unteren rechten Ecke klickt und festhält, kann man die Grösse des Elementes frei verändern.


### Zahlenfeld { .fs-5 }



Ein Element das nur Zahlenwerte akzeptiert. Je nach Konfiguration lässt es manche Werte nicht zu (z.B. negative Zahlen für Jahrgang). Mit den kleinen Knöpfchen an der rechten Seite des Elementes lässt sich durch den zulässigen Wertebereich scrollen. Wenn der Fokus im Element liegt (also wenn der
 [Cursor](https://en.wikipedia.org/wiki/de:Cursor "wikipedia:de:Cursor") im Element zu sehen ist), kann auch mit dem Mausrad gescrollt werden.
 



### Checkbox { .fs-5 }



Ein Element für Wahrheitswerte. Wenn die Beschriftung des Elementes zutrifft, dann mit Mausklick ein Häkchen setzen.



### Auswahlfelder


### Einfaches Auswahlfeld/Drop-Down { .fs-5 }



Beim Klicken auf dieses Feld klappt sich ein Menü auf ("drop down"), aus dem man eine der Optionen wählen kann.



### Kombinationsfeld/Combobox { .fs-5 }



Kombination aus einem Textfeld und einem Auswahlfeld/Listenfeld, das mittels Texteingabe das Durchsuchen der Listeneinträge möglich macht. Im oberen Bereich kann der Suchtext eingegeben werden, im unteren Bereich werden Suchergebnisse angezeigt, von denen dann ein Eintrag per Mausklick ausgewählt werden kann. Per Mausrad lässt sich durch die Ergebnisse scrollen.

  

Die Auswahl kann aufgehoben werden, indem man auf das kleine "**x**" am rechten Ende des Elementes klickt.

[![Combobox mit Auswahl](/mediawiki/images/2/25/Widget_autocomplete_selected.png)](datei:widget_autocomplete_selected.png.md "Combobox mit Auswahl")

  

Manche Combobox Elemente lassen auch die Erstellung von neuen
 [Datensätzen](datensatz.md "Datensatz") zu, sofern zu dem Suchbegriff kein
 *exakter* Eintrag gefunden werden konnte. Am unteren Ende des Elementes erscheint ein Eintrag mit dem Text "Erstelle <Suchtext>". Klickt man auf diesen Eintrag wird ein entsprechender Datensatz zu der Datenbank hinzugefügt.
 

[![Schnellerstellung](/mediawiki/images/8/88/Widget_autocomplete_create.png)](datei:widget_autocomplete_create.png.md "Schnellerstellung")


### Combobox mit Mehrfachauswahl { .fs-5 }



Im Gegensatz zur normalen Combobox können hier mehrere Listeneinträge ausgewählt werden. Ausgewählte Einträge können durch einen Klick auf das kleine "**x**" in der
 ***linken*** Ecke des Eintrages wieder entfernt werden. Wie auch bei der Combobox lässt sich die
 *gesamte* Auswahl durch einen Klick auf das "**x**" am rechten Ende aufheben.
 


### gefilterte Mehrfachauswahl { .fs-5 }



Dieses Bedienelement erfüllt denselben Zweck wie die Combobox mit Mehrfachauswahl, unterscheidet sich jedoch etwas in der Funktionsweise. In das Textfeld neben dem Lupensymbol kann ein Suchbegriff eingegeben werden, mit welchem die Liste gefiltert wird.
Auf der linken Seite befinden sich die Ergebnisse, auf der rechten Seite die vorgenommene Auswahl. Einzelne Einträge können mittels Doppelklick in die jeweils andere Liste verschoben werden. Um mehrere Einträge auszuwählen, muss die Strg-Taste während des Klickens gedrückt gehalten werden. Alternativ dazu können mehrere nebeneinander liegende Einträge auch durch Festhalten der linken Maustaste ausgewählt werden. Die Auswahl kann dann mithilfe der Pfeil-Knöpfe verschoben werden.


### Spezialfelder


### Datumsfeld { .fs-5 }



Ein Feld für vollständige Datumsangaben. Akzeptiert Angaben in der Form TT.MM.JJJJ (Tag.Monat.Jahr) und JJJJ-MM-TT (Jahr-Monat-Tag,
 [ISO 8601](https://en.wikipedia.org/wiki/de:ISO_8601 "wikipedia:de:ISO 8601")). Daneben befinden sich zwei Hilfswerkzeuge; das erste fügt das heutige Datum direkt in das Feld ein, das zweite öffnet einen Kalender zur Auswahl des Tages.
 


### Feld für partielles Datum { .fs-5 }



Ein Feld mit dem Datumsangaben gemacht werden können, die nicht unbedingt vollständig sein müssen: zum Beispiel Monat 8 und Jahr 1986 aber ohne Tag.


### Laufzeitfeld { .fs-5 }



Dieses Feld rechnet Angaben in ein zeitliches Format hh:mm:ss (Stunden:Minuten:Sekunden) um.

  

Angaben, die dem Format nicht vollständig entsprechen, werden akzeptiert und ggf. umgerechnet:





| Eingabetext | Entspricht | | | | Ergebnis |
| --- | --- | --- | --- | --- | --- |
|  | Stunden | Minuten | Sekunden | Anmerkung |  |
| 20 | 00 | 00 | 20 | 20 Sekunden | 00:00:20 |
| 120 | 00 | 02 | 00 | 120 Sekunden | 00:02:00 |
| 1:20 | 00 | 01 | 20 | 1 Minute und 20 Sekunden | 00:01:20 |
| 1:80 | 00 | 02 | 20 | 1 Minute und 80 Sekunden | 00:02:20 |
| 90:10 | 01 | 30 | 10 | 90 Minuten und 10 Sekunden | 01:30:10 |
| 1:30:10 | 01 | 30 | 10 | 1 Stunde, 30 Minuten und 10 Sekunden | 01:30:10 |




### ISSN/ISBN/EAN { .fs-5 }



Ein Feld, welches Angaben für Standardnummern wie ISSN, ISBN oder EAN akzeptiert, validiert und in ein gut lesbares Format umwandelt.
Aus einer ISBN ohne Formatierung:

... wird automatisch nach Speicherung eine ISBN mit Bindestrichen:

[![ISBN Feld mit formatiertem Text](/mediawiki/images/9/97/Widget_isbn_formatted.png)](datei:widget_isbn_formatted.png.md "ISBN Feld mit formatiertem Text")

  

Anmerkung: Umwandlungen von ISBN-10 zu ISBN-13 und von EAN zu ISSN werden automatisch vorgenommen.

### Ändern/Hinzufügen/Löschen


Der Kern der Datenbank sind die
 [Beziehungen](https://en.wikipedia.org/wiki/de:Relationale_Datenbank "wikipedia:de:Relationale Datenbank") zwischen den Tabellen. Ein Musiker kommt aus Dortmund, weil im
 [Datensatz](datensatz.md "Datensatz") des Musikers aus der Musiker Tabelle eine Beziehung zum Datensatz Dortmund aus der Tabelle der Orte existiert. Steuerelemente wie das Auswahlfeld oder die Combobox dienen dazu, die Herstellung und Verwaltung dieser Beziehungen zu vereinfachen. Zu diesem Zweck findet man neben diesen Elementen meist weitere Elemente, die das Hinzufügen eines neuen oder das Bearbeiten/[Löschen](l%c3%b6schen.md "Löschen") eines bereits existierenden "fremden" Datensatzes ermöglichen.
   

 Für die ausgewählte Ausgabe "2000-1", von links nach rechts: Ausgabe bearbeiten, neue Ausgabe hinzufügen, Ausgabe löschen.







### Inlines


Die meisten Formulare enthalten Inlines. Kurz und knapp gesagt, sind das Formulare von verwandten Datensätzen, die in dem Hauptformular eingebettet sind. Wenn man beispielsweise einem Artikel einen Musiker hinzufügt, so tut man dies mithilfe vom Inline für die Artikel-Musiker Beziehung.



Dabei werden einzelne Musiker zeilenweise angegeben; jede Zeile entspricht dabei einem kleinen Formular. Neue Zeilen - und damit ein neues, leeres Formular - können mit dem "Musiker hinzufügen" Knopf am unteren Ende des Inlines hinzugefügt werden. Diese zusätzlichen, neu hinzugefügten Formulare können mit dem Knopf "**x**" am rechten Ende der Zeile wieder entfernt werden (nicht zu verwechseln mit dem
 **x** der [Combobox Elemente](#Kombinationsfeld.2FCombobox)!).



Um
 *abgespeicherte* Beziehungen zu entfernen, muss unter "**Löschen**" in der jeweiligen Zeile ein Häkchen gesetzt und der Artikel abgespeichert werden.  

 Anmerkung: das x in der Combobox hebt nur die Auswahl des Bedienelementes auf. Das führt nicht nur
 *nicht* zur Löschung der Beziehung, sondern sogar direkt zu folgender Fehlermeldung, da das Element nicht leer - also ohne Auswahl - bleiben darf: "Dieses Feld ist zwingend erforderlich."


