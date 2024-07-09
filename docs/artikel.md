Artikel
=======


In dieser Kategorie werden Artikel aus Zeitschriften gesammelt.

## Erfassung

Die Erfassung der Zeitungsartikel ist recht unkompliziert und ist damit gut für Anfänger als Einleitung in die Datenbank
geeignet.
Zu dem Zweck der Einführung in die Datenbank ist diese Anleitung hier auch ein wenig ausführlicher.

Mal angenommen, ihr habt euch ein Heft des Magazins "Rolling Stone" zum Erfassen ausgesucht.
Um mit der Erfassung zu beginnen, solltet ihr zuerst die Datenbank nach vorhandenen Artikel dieses Heftes durchsuchen.

### Vorhandene Artikel suchen { .fs-5 }

In Kurzform:

* im [Index/Hauptmenü](oberfl%c3%a4che.md#Index "Oberfläche") auf "Artikel" klicken
* im [Suchformular](suchformular.md "Suchformular") auf "Erweiterte Suchoptionen anzeigen" klicken
* im Suchformular das Feld "[Magazin](magazin.md "Magazin")" anklicken, den Namen des Magazins eintippen und dann das
  entsprechende Magazin aus der Liste auswählen
* danach im Feld "Ausgabe" das Jahr der Ausgabe eingeben und die entsprechende Ausgabe auswählen
* auf "Suchen" klicken

<div markdown class="d-flex justify-content-evenly gap-5 text-center">
<figure markdown="span">
  ![Artikel Suchformular](img/artikel_suchformular.png){ width="300" .mb-1 }
  <figcaption>Artikel Suchformular</figcaption>
</figure>
<figure markdown="span">
  ![Magazin auswählen](img/artikel_magazin_select.png){ width="300" .mb-1 }
  <figcaption>Magazin auswählen</figcaption>
</figure>
<figure markdown="span">
  ![Ausgabe Auswählen](img/artikel_ausgabe_select.png){ width="300" .mb-1 }
  <figcaption>Ausgabe Auswählen</figcaption>
</figure>
</div>



Daraufhin werden euch die Artikel des Heftes angezeigt, die bereits in der Datenbank eingetragen wurden.

!!! info "Praktisch"
    Durch die Suche werden die Angaben zu Magazin und Ausgabe im Suchformular an die Formulare für neue Artikel
    weitergereicht und dort in die entsprechenden Felder automatisch eingefügt. Dadurch erspart ihr euch etwas Arbeit.

### Neuen Artikel erstellen { .fs-5 }

Nun sucht ihr euch aus der Zeitschrift den Artikel heraus, der noch nicht in die Datenbank eingetragen wurde und den ihr
erfassen wollt.
Um mit der Erfassung zu beginnen, klickt ihr auf den Knopf "Artikel hinzufügen".
Es wird euch nun ein leeres Formular angezeigt, in das ihr die Daten des Artikels eintragen könnt.

Zunächst solltet ihr die Grunddaten des Artikels eintragen, damit man anhand der Daten im
Artikel-[Datensatz](datensatz.md "Datensatz") zu dem
"echten" Artikel in der physischen Zeitschrift gelangen kann.
Dazu gebt ihr das **Magazin**, die **Ausgabe** (diese sollten bereits eingetragen sein, sofern ihr die [Suche](#Suche)
gemacht habt),
die **Schlagzeile** und die **Seite**, wo der Artikel beginnt, ein.
Der Datensatz der Ausgabe gibt den [Lagerort](lagerort.md "Lagerort") des Heftes an, und mit der Schlagzeile und der
Seitenangabe sollte man den Artikel schnell im Heft wiederfinden können.

Je nach Artikel ist es manchmal nicht ganz klar, was die Schlagzeile eines Artikels ist. Lasst euch davon nicht
entmutigen; die Schlagzeile dient schlicht als Erkennungsmerkmal und ist nicht so sehr wichtig.
Tragt also das ein, was ihr als Schlagzeile erachtet. Oder schaut im Inhaltsverzeichnis der Ausgabe nach, was dort als
Titel angegeben ist.

Habt ihr diese Angaben gemacht, solltet ihr erst einmal zwischenspeichern, indem ihr unten auf den Knopf mit der
Aufschrift "Sichern und weiterbearbeiten" klickt.

!!! warning "Wichtig!"
    Änderungen werden nur übernommen, wenn ihr auf einen der "[Sichern](sichern.md "Sichern")" Knöpfe klickt.
    Verlasst ihr das Formular (z.B. indem ihr das Fenster schließt oder zu einer anderen Seite navigiert), ohne es zu
    sichern, geht eure Arbeit verloren!
    Es sollte eine Warnung auftauchen, wenn ihr versucht, ein Formular mit ungespeicherten Änderungen zu verlassen.

!!! info "Welche Artikel müssen erfassen werden und welche nicht?"
    Prinzipiell **müssen** alle Texte erfasst werden, die einen Bezug zur Musikern, Bands oder zur Musik im Allgemeinen
    aufweisen.
    Davon ausgenommen sind Kurznachrichten und Reviews von Alben und Tonträgern. Aus Zeitgründen müsst ihr diese nicht in
    Datenbank eintragen (ihr *könnt* es aber, wenn ihr wollt).

Im [Hauptmenü](oberfl%c3%a4che.md#Index "Oberfläche") klickt ihr zuerst auf "Artikel", um zur
[Änderungsliste](%c3%84nderungsliste.md "Änderungsliste") zu gelangen.
In dieser solltet ihr nach Magazin und Ausgabe filtern und eine Suche ausführen.
Dazu klickt ihr zunächst auf "Erweiterte Suchoptionen anzeigen", damit die restlichen Felder
des [Suchformulars](suchformular.md "Suchformular") angezeigt werden.
Wenn ihr dann das Feld Magazin anklickt, könnt ihr den Namen des Magazins eingeben und dann in den Ergebnissen das
passende Magazin auswählen.

Damit überprüft ihr, ob bereits Artikel zu der jeweiligen Ausgabe erfasst wurden. Außerdem werden die Angaben zu Magazin
und Ausgabe aus dieser Änderungsliste heraus an Formulare für neue Artikel weitergereicht und dort in die entsprechenden
Felder automatisch eingefügt. Dadurch erspart ihr euch später etwas Arbeit.

Klickt dazu auf das
[Bedienelement](bedienelement.md "Bedienelement") neben "Magazin", und tippt den Namen (Anfangsbuchstaben reichen) des
Magazins ein. Im
[Dropdown Menü](bedienelement.md#Kombinationsfeld.2FCombobox "Bedienelement") des Ausgabenfeldes werden daraufhin die
Ausgaben dieses Magazins angezeigt, aus denen ihr nun die entsprechende heraus suchen könnt. Um eine Ausgabe zu finden,
ist meistens das Jahr als Suchtext ausreichend. Insbesondere dann, wenn ihr nicht wisst, wie der
[Titel](ausgabe.md#Textliche_Darstellung "Ausgabe") der Ausgabe in der Datenbank genau lautet, kann eine zu enge Suche
ins Nichts führen: wenn euer Suchtext etwas enthält, was es so nicht in Datenbank gibt, dann wird auch nichts gefunden
werden.
Habt ihr Magazin und Ausgabe angegeben, dann klickt ihr weiter unten auf den "Suche" Knopf, um die Suche nach Artikel
dieser Ausgabe zu starten. Werden keine Ergebnisse gefunden, oder ist zumindest der entsprechende Artikel noch nicht
vorhanden, dann klickt auf den Knopf "Artikel hinzufügen", um zu dem Formular für
Artikel-[Datensätze](datensatz.md "Datensatz") zu gelangen.

Nun müssen Daten erfasst werden, mit denen man vom Datensatz des Artikels in einer Datenbank zu dem "echten" Artikel in
der Zeitschrift kommen kann. Dazu gehören der Name des Magazins, die jeweilige Ausgabe, die Schlagzeile und die
Seitenzahl. Sofern ihr die Suche aus dem ersten Punkt gemacht habt, sind Magazin und Ausgabe bereits eingetragen. Ist
das nicht der Fall, so müsst ihr zunächst das richtige Magazin auswählen. Danach müsst ihr die Ausgabe auswählen. Die
Angabe zur Schlagzeile hilft beim Erkennen des Artikels auf einer Seite und sollte dementsprechend wortgetreu
eingetragen werden. Der
[Lagerort](lagerort.md "Lagerort") des Heftes ist in der Ausgabe angegeben. Jetzt fehlt einer an dem Artikel
interessierten Person nur noch eine Seitenangabe und sie kann anhand der Daten von der Datenbank genau und problemlos
zum echten Zeitungsartikel in der Zeitung gelangen. Um eine Einschätzung des Umfangs des Artikels zu ermöglichen, sollte
die Anzahl der Seiten des Artikels festgehalten werden (siehe
<#Seitenumfang>).

Jetzt kommt der wichtigste und aufwendigste Teil: es gilt, Daten bezüglich des Inhaltes des Artikels einzutragen. Diese
Daten sind deshalb so wichtig, da der jeweilige Artikel dank ihnen "gefunden" werden kann. Eine Person, die gar nichts
von diesem Artikel weiß, kann auf diesen Artikel treffen, wenn er als Ergebnis einer Suchanfrage auftaucht. Damit der
Artikel als Teil der Ergebnisse gelten kann, müssen die Suchkriterien und die im Datensatz gemachten Angaben ähnlich
oder gleich sein. Für euch bedeutet das:




> **macht ihr keine Angaben, kann der Artikel auch nie gefunden werden. Und macht ihr viele ungenaue oder überflüssige
Angaben, so kann der Artikel unerwünscht als Ergebnis auftauchen.**


Beispiel: wenn in einem Artikel beiläufig die Beatles erwähnt werden, und ihr trotzdem Beatles als Band angebt, wird
dieser Artikel auch in jeder Suche nach Beatles auftauchen, obwohl eigentlich kaum Bezug zu der Band besteht.
Grundsätzlich sollten die Angaben den Kern des Artikels wieder spiegeln. Im Zweifelsfall ist es jedoch besser, eher mehr
als weniger Angaben zu machen: ein Datensatz, der nicht gefunden werden kann, bringt schließlich auch nichts.

Nachdem ihr den Artikel durchgelesen habt, solltet ihr dem Datensatz eine kurze textliche Zusammenfassung des Artikels
hinzufügen. Anhand der Zusammenfassung soll eine recherchierende Person einschätzen können, ob der Artikel für sie
interessant ist oder nicht. Dazu kommt, dass der Inhalt des Feldes in die Volltextsuche miteinbezogen wird und damit zum
Wiederfinden des Artikels beiträgt.

Danach werden in den jeweiligen Bereichen weiter unten zusätzliche Angaben wie Autor, Musiker, Band, Schlagwort, usw.
festgehalten.

Anzumerken ist, dass ihr hier von *anderen* Datensätzen (aus anderen Bereichen der Datenbank, siehe
[Bedienelement#Inlines](bedienelement.md#Inlines "Bedienelement")) auswählt und dass ihr mit dieser Auswahl Verbindungen
zwischen dem Datensatz des Artikels und den anderen Datensätzen herstellt: wenn man dem Artikel die Band "The Beatles"
zuweist, wird anders herum auch ein Verweis auf diesen Artikel in dem Datensatz der Beatles hinterlegt.

Wenn ihr mit der Erfassung dieses Artikels fertig seid und direkt den nächsten erfassen wollt, klickt
auf "[Sichern](sichern.md "Sichern") und neu hinzufügen". Der Artikel wird abgespeichert, es wird ein neues, leeres
Formular angezeigt und das Magazin und die Ausgabe werden eingefügt (sofern ihr, wie vorgeschlagen, die Suche mit der
Änderungsliste gemacht habt).

### Ausnahmen { .fs-5 }

Prinzipiell kann jeder Text einer Ausgabe erfasst und eingetragen werden. Jedoch haben manche Abschnitte wenig
Informationsgehalt: News mit einem Umfang von 20 Wörtern haben meist nicht viel Aussagekraft. Aus Zeitgründen ist die
Richtlinie daher, dass nur echte Artikel erfasst werden
*müssen* und andere Texte eher nicht erfasst werden
*sollten.* Ein "echter Artikel" wäre z.B. etwas, das im Inhaltsverzeichnis erwähnt wird, eine Autorenangabe hat oder
etwas, das über eine gewisse Länge hinaus geht. "Andere Texte" wären dann News oder Rezensionen von Veröffentlichungen (
also z.B. Reviews von Musikalben). Ob etwas Informationsgehalt hat, bemerkt ihr dann, wenn ihr die Zusammenfassung
schreiben wollt: fällt die Zusammenfassung sehr dünn aus, ist das ein Indiz dafür, dass ihr den Text nicht aufnehmen
braucht.
Am Ende unterliegt es immer eurer Einschätzung, welcher Text erfasst wird. Findet ihr eine News, die ihr für wichtig
oder erwähnenswert haltet, könnt ihr diese erfassen.

## Formularfelder

### Magazin { .fs-5 }

Das [Magazin](magazin.md "Magazin") der Ausgabe, welche den Artikel enthält.

### Ausgabe { .fs-5 }

Die [Ausgabe](ausgabe.md "Ausgabe"), welche den Artikel enthält.
Um nach einer Ausgabe suchen zu können, muss ein Magazin ausgewählt sein.

### Schlagzeile { .fs-5 }

Die Schlagzeile des Artikels wie sie im Heft steht. Die Angabe hier soll dazu dienen, den entsprechenden Artikel auf
einer Seite wiederfinden zu können.

### Seite { .fs-5 }

Zahl der Anfangsseite des Artikels.

### Seitenumfang { .fs-5 }

Mit dieser Angabe soll erkennbar gemacht werden, wie umfangreich der Artikel ist. Umfasst der Artikel nur die eine
Seite, so muss hier keine Angabe gemacht werden. Bei zwei Seiten '**f'**, und bei mehr als zwei Seiten '**ff'**.

### Zusammenfassung { .fs-5 }

Ein kurzer Text, der die wichtigsten Aspekte und Themen des Artikels aufführt.

### Beschreibung { .fs-5 }

Ein Feld für weitere Angaben, welche in kein anderes der Felder passen.

### Bemerkungen { .fs-5 }

Notizen für Archiv-Mitarbeiter. Nur Mitarbeiter können dieses Felder sehen.



---

### Autoren { .fs-5 }

Die
[Autoren](autor.md "Autor") des Artikels sollen hier gelistet werden. Zur Erklärung des Such-Dropdowns siehe:
[Autor#Schnellerstellung mit Dropdown](autor.md#Schnellerstellung_mit_Dropdown "Autor")

### Musiker { .fs-5 }

Bezieht sich der Artikel auf
[Musiker](musiker.md "Musiker"), so sollen diese hier angegeben. Bezieht sich der Artikel auf eine Band, müssen die
Mitglieder der Band hier nicht zusätzlich ausgewählt werden.

### Bands { .fs-5 }

Angabe der im Artikel besprochenen [Bands](band.md "Band").

### Schlagwörter { .fs-5 }

[Schlagwörter](schlagwort.md "Schlagwort")/Deskriptoren/Tags zur Art (Interview, Porträt, usw.) und zum Themenbereich (
z.B. '60er Jahre') des Artikels.

### Genres { .fs-5 }

Geht es im Artikel um bestimmte
[Genres](genre.md "Genre") (z.B. ein Artikel über die Geschichte des Jazz), so sollen diese hier angegeben werden.
Genres von oben ausgewählten Musikern oder Bands müssen nicht nochmals gelistet werden.

### Orte { .fs-5 }

Auflistung der [Orte](ort.md "Ort"), auf die sich der Artikel bezieht.
Herkunftsorte der Musiker, Bands, Autoren, usw. müssen hier nicht angegeben werden.

### Spielorte { .fs-5 }

Auflistung der
[Spielorte](spielort.md "Spielort") (also: Venues, Locations), auf die sich der Artikel bezieht.

### Veranstaltungen { .fs-5 }

Werden in dem Artikel bestimmte
[Veranstaltungen](veranstaltung.md "Veranstaltung") (also: Konzerte, Festivals) behandelt, so sollen diese hier
angegeben werden.

### Personen { .fs-5 }

Angaben zu im Artikel benannten
[Personen](person.md "Person"), die weder Autoren noch Musiker sind (z.B. Produzenten).

Die Personendaten der bereits gelisteten Autoren und Musiker müssen nicht nochmals gelistet werden.

### Anmerkungen zu Ort, Spielort, Verantsaltung

Hier einige Beispiele, die die Unterschiede zwischen und die Verwendungszwecke von
[Ort](ort.md "Ort"), [Spielort](spielort.md "Spielort") und
[Veranstaltung](veranstaltung.md "Veranstaltung") deutlich machen sollen.

* ein Artikel über Musikszene in Dortmund

'[Orte](artikel.md#Orte "Artikel")' sollte einen Ort `Dortmund` enthalten.

* Artikel über den Jazzclub 'domicil' in Dortmund

'Spielorte' sollte einen Spielort `domicil` enthalten. Da im Spielort `domicil` der Ort
`Dortmund` bereits vermerkt ist, *muss* der Ort
`Dortmund` nicht noch einmal extra unter 'Orte' gelistet werden - der Vollständigkeit halber kann das aber getan werden.

* Artikel über ein Konzert im domicil in Dortmund

Eine dem Konzert entsprechende Veranstaltung sollte unter 'Veranstaltungen' angegeben werden. Wie auch im vorigen
Beispiel müssen Angaben, die in der Veranstaltung bereits enthalten sind (also: der Spielort
`domicil` und der Ort des Spielortes `Dortmund`) nicht zwingend zusätzlich gelistet werden.
 
