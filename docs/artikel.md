Artikel
=======


In dieser Kategorie werden Artikel aus Zeitschriften gesammelt.

## Erfassung { .fs-3 }

Die Erfassung der Zeitungsartikel ist recht unkompliziert und ist damit gut für Anfänger als Einleitung in die Datenbank
geeignet.
Deine Aufgabe ist es, die wichtigsten Informationen, die in einem Artikel enthalten sind, in die Datenbank einzufügen,
sodass der Artikel bei einer Suche wiedergefunden werden kann.

Für ein Beispiel nehmen wir mal an, dass du einen Artikel aus einem Heft des "Rolling Stone" Magazins erfassen willst.
Um mit der Erfassung zu beginnen, solltest du zuerst die Datenbank nach vorhandenen Artikel dieses Heftes durchsuchen.

### Vorhandene Artikel suchen { .fs-5 }

Bevor du einen neuen Artikel hinzufügst, solltest du erst schauen, ob dieser schon in der Datenbank existiert.
Ist der Artikel bereits erfasst, solltest du ihn nicht noch einmal eintragen.

So suchst du nach den Artikeln eines Heftes:

1. im [Index/Hauptmenü](oberfläche.md#Index "Oberfläche") auf "Artikel" klicken
2. im [Suchformular](suchformular.md "Suchformular") auf "Erweiterte Suchoptionen anzeigen" klicken
3. im Suchformular das Feld "[Magazin](magazin.md "Magazin")" anklicken, den Namen des Magazins eintippen und dann das
   entsprechende Magazin aus der Liste auswählen
4. danach im Feld "Ausgabe" das Jahr der Ausgabe eingeben und die entsprechende Ausgabe auswählen
5. auf "Suchen" klicken

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



Daraufhin werden dir die Artikel des Heftes angezeigt, die bereits in der Datenbank eingetragen wurden.

[comment]: # (@formatter:off)
!!! info "Praktisch"
    Durch die Suche werden die Angaben zu **Magazin** und **Ausgabe** im Suchformular an die Formulare für neue Artikel
    weitergereicht und dort in die entsprechenden Felder automatisch eingefügt. Dadurch ersparst du dir etwas Arbeit.

[comment]: # (@formatter:on)

### Neuen Artikel erstellen { .fs-5 }

Nun suchst du dir aus der Zeitschrift den Artikel heraus, **der noch nicht in die Datenbank eingetragen wurde** und den
du erfassen willst. Um mit der Erfassung zu beginnen, klicke auf den Knopf "Artikel hinzufügen". Es wird ein leeres
Formular angezeigt, in das du die Daten des Artikels eintragen kannst.

<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Artikel hinzufügen](img/artikel_hinzufügen_btn.png){ width="300" .mb-1 }  
  <figcaption>Artikel hinzufügen</figcaption>  
</figure>
<figure markdown="span">  
  ![Artikel Formular](img/artikel_formular.png){ width="300" .mb-1 }  
  <figcaption>Artikel Formular</figcaption>  
</figure>
</div>

Zunächst solltest du die Grunddaten des Artikels eintragen, damit man anhand der Daten im
Artikel-[Datensatz](datensatz.md "Datensatz") zu dem "echten" Artikel in der physischen Zeitschrift gelangen kann. Dazu
gibst du das **Magazin**, die **Ausgabe** (diese sollten bereits eingetragen sein, sofern du
die [Suche](#vorhandene-artikel-suchen) gemacht hast), die **Schlagzeile** und die **Seite**, wo der Artikel beginnt,
ein.

Je nach Artikel ist es manchmal nicht ganz klar, was die Schlagzeile eines Artikels ist. Lasse dich davon nicht
entmutigen; die Schlagzeile dient schlicht als Erkennungsmerkmal und ist inhaltlich nicht so sehr wichtig.
Trage also das ein, was du als Schlagzeile erachtest. Oder schaue im Inhaltsverzeichnis der Ausgabe nach, was dort als
Titel angegeben ist.

Hast du diese Angaben gemacht, solltest du erst einmal zwischenspeichern, indem du unten auf den Knopf mit der
Aufschrift "Sichern und weiterbearbeiten" klickst.


<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Speicher Knöpfe](img/sichern.png){ width="300" .mb-1 }  
  <figcaption>Speicher Knöpfe</figcaption>  
</figure>
</div>

Da der Datensatz der Ausgabe den [Lagerort](lagerort.md "Lagerort") des Heftes angibt, hat man nun alle Angaben zur
Hand, die man braucht, um den Artikel im "echten" Heft wiederzufinden.

[comment]: # (@formatter:off)
!!! warning "Abspeichern ist notwendig!"
    Änderungen werden nur übernommen, wenn du auf einen der "[Sichern](sichern.md "Sichern")" Knöpfe klickst.
    Verlässt du das Formular (z.B. indem du das Fenster schließt oder zu einer anderen Seite navigierst), ohne es zu
    sichern, geht deine Arbeit verloren!
    Es sollte eine Warnung auftauchen, wenn du versuchst, ein Formular mit ungespeicherten Änderungen zu verlassen.

[comment]: # (@formatter:on)

### Artikel Inhalt aufnehmen { .fs-5 }

Bisher hast du nur Angaben zu dem Heft, der Schlagzeile und der Seitenzahl gemacht. Das ist aber noch nicht
aussagekräftig genug, denn über den Inhalt des Artikels hast du noch keine Angaben gemacht.
Also ist es jetzt an der Zeit, dass du dir den Artikel einmal durchliest. Anschließend solltest du eine
Zusammenfassung des Artikels in das entsprechende Feld des Formulars eintragen.

Anhand der Zusammenfassung werden Recherchierende feststellen können, ob der Artikel für sie interessant ist oder nicht.
Dementsprechend solltest du dir hier Mühe geben, die relevanten Teile eines Artikels anzugeben. Dabei ist es wichtiger,
dass alle wichtigen, interessanten Informationen enthalten sind, als dass du einen schönen Text schreibst. Wenn es dir
leichter fällt, kannst du anstelle von Fließtext auch Stichpunkte benutzen. Hauptsache die Informationen sind
eingetragen. Die Zusammenfassung wird in die Volltextsuche miteinbezogen; d.h. ein Artikel kann anhand der Angaben in
der Zusammenfassung wiedergefunden werden.

[comment]: # (@formatter:off)  
!!! info "Nur Relevantes eintragen"
    Machst du keine Angaben, kann der Artikel auch nie gefunden werden. Machst du hingegen viele ungenaue oder 
    überflüssige Angaben, so kann der Artikel unerwünscht als Ergebnis auftauchen. Trage also nur das ein, was für den
    Artikel relevant ist, oder was für das Thema des Artikels von Bedeutung ist.<br>  
    **Beispiel**: Wird in einem Artikel eine Band nur beiläufig erwähnt, so solltest du diese Band nicht erwähnen.

[comment]: # (@formatter:on)

[comment]: # (@formatter:off)  
!!! info "Textfeld zu klein?"  
    Manche Textfelder, wie z.B. "Zusammenfassung", kannst du vergrößern oder verkleinern, in dem du im Textfeld unten 
    rechts auf das kleine Symbol klickst, die Maustaste gedrückt hältst und dann die Maus rauf- oder runterbewegst. 

[comment]: # (@formatter:on)

### Verknüpfungen hinzufügen { .fs-5 }

Neben der Volltextsuche lassen sich Artikel auch über Verknüpfungen (oder Beziehungen) mit anderen Datensätzen, wie zum
Beispiel mit Bands oder Musikern, finden. Eine solche Verknüpfung hast du bereits gesehen: die Ausgabe. Ein Artikel ist
immer mit einer Ausgabe, dem Heft, verknüpft. Wenn du neben der Ausgabe auf den kleinen grünen Bleistift klickst,
gelangst du auf die Änderungsseite der Ausgabe. Und andersherum gelangst du von der Änderungsseite der Ausgabe zu einer
Auflistung aller Artikeln dieser Ausgabe, indem du unter dem Namen der Ausgabe auf den Link mit der Beschriftung
"Artikel" klickst.


<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Ausgabe ändern Knopf](img/artikel_edit_ausgabe.png){ width="300" .mb-1 }  
  <figcaption>Ausgabe ändern Knopf</figcaption>  
</figure>
<figure markdown="span">  
  ![Artikel einer Ausgabe](img/ausgabe_related_link.png){ width="300" .mb-1 }  
  <figcaption>Artikel einer Ausgabe</figcaption>  
</figure>
</div>

Weitere Verknüpfungen kannst du unten auf der Artikelseite hinzufügen. Um beispielsweise eine Verknüpfung zwischen dem
Artikel und der Band "The Rolling Stones" herzustellen, klicke unten auf den Reiter mit der Aufschrift "Band" (1).
Klicke dann in ein leeres Dropdown-Feld (2) und gebe im Dropdown-Menü den Namen der Band ein (3). Aus der Ergebnisliste
wählst du dann die entsprechende Band mit einem Klick aus (4).
Mit dem Knopf "Änderungsliste" (5) rufst du die Ergebnisse in der Bands-Übersichtsseite auf - hier kannst du die
Ergebnisse genauer anschauen.
Findest du keine passende Band, kannst du mit dem Knopf "Hinzufügen" (6) eine neue Band erstellen.

Um eine weitere Verknüpfung hinzuzufügen, klicke auf den Knopf "Band hinzufügen". Daraufhin erscheint ein weiteres
Dropdown-Element in einer neuen Zeile.
Um eine Verknüpfung zu entfernen, klicke auf das rote "X" in der entsprechenden Zeile. Die Zeile wird daraufhin zur
Löschung markiert. Wenn du den Artikel abspeicherst, wird die *Verknüpfung* gelöscht. Der Datensatz, der mit dem Artikel
verknüpft war (also hier die Band "Rolling Stones"), wird dabei *nicht* gelöscht - nur die Verknüpfung zwischen dem
Artikel und der Band wird gelöscht.


<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Verknüpfung mit einer Band hinzufügen](img/band_select.png){ width="300" .mb-1 }  
  <figcaption>Verknüpfung mit einer Band hinzufügen</figcaption>  
</figure>
<figure markdown="span">  
  ![Hinzufügen & Löschen](img/band_inline_add_delete.png){ width="300" .mb-1 }  
  <figcaption>Hinzufügen & Löschen</figcaption>  
</figure>
</div>

[comment]: # (@formatter:off)  
!!! warning "Ausreichend Angaben machen"  
    Wenn du eine neue Band erstellst, solltest du mehr Informationen als nur den Namen hinterlegen. Es kommt häufig vor, 
    dass zwei Bands denselben Namen haben. Um diese voneinander unterscheiden zu können, solltest du weitere Angaben wie
    zum Beispiel Genres, Aliase oder Links zu Wikipedia oder Discogs machen. Dies gilt [grundsätzlich](grundsätze.md) 
    für alle Arten von Datensätzen.<br>  
    Hast du für die Erstellung den "Hinzufügen" Knopf des Dropdown-Menüs benutzt, kannst du auf den Bleistift neben der
    erstellten Band klicken, um zu der Änderungsseite zu gelangen.
    
[comment]: # (@formatter:on)

[comment]: # (@formatter:off)
!!! info "Duplikate vermeiden"
    Grundsätzlich solltest du es vermeiden, Duplikate zu erstellen; ist zum Beispiel eine Band bereits in der Datenbank 
    eingetragen, so solltest du nicht eine weitere Band mit demselben Namen hinzufügen (es sei denn es ist eine komplett
    andere Band, die den denselben Namen hat).

[comment]: # (@formatter:on)

### Bearbeitung abschließen {.fs-5}

Wenn du mit der Erfassung dieses Artikels fertig bist und direkt den nächsten erfassen willst, klicke
auf "[Sichern](sichern.md "Sichern") und neu hinzufügen". Der Artikel wird abgespeichert, es wird ein neues, leeres
Formular angezeigt und das Magazin und die Ausgabe werden eingefügt (sofern du, wie vorgeschlagen,
die [Suche](#vorhandene-artikel-suchen--fs-5-) mit der Übersichtsseite gemacht hast).

Drückst du auf "Sichern und weiterbearbeiten" wird der Artikel abgespeichert und das Formular für den Artikel neu
geladen.
Mit dem "Sichern" Knopfs gelangst du, nachdem der Artikel gespeichert wurde, zurück zu der Übersichtsliste der Artikel.

<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Speicher Knöpfe](img/sichern.png){ width="300" .mb-1 }  
  <figcaption>Speicher Knöpfe</figcaption>  
</figure>
</div>

## Ausnahmen: Welche Artikel müssen erfasst werden und welche nicht? { .fs-5 }

Prinzipiell kann jeder Text einer Ausgabe erfasst und eingetragen werden. Jedoch haben manche Abschnitte wenig
Informationsgehalt: News mit einem Umfang von 20 Wörtern haben meist nicht viel Aussagekraft. Aus Zeitgründen ist die
Richtlinie daher, dass nur echte Artikel erfasst werden *müssen* und andere Texte eher nicht erfasst werden *sollten.*
Ein "echter Artikel" wäre z.B. etwas, das im Inhaltsverzeichnis erwähnt wird, eine Autorenangabe hat oder etwas, das
über eine gewisse Länge hinaus geht. "Andere Texte" wären dann News oder Rezensionen von Veröffentlichungen (also z.B.
Reviews von Musikalben). Ob etwas Informationsgehalt hat, bemerkst du dann, wenn du die Zusammenfassung schreiben
willst: fällt die Zusammenfassung sehr dünn aus, ist das ein Indiz dafür, dass du den Text nicht aufnehmen brauchst. Am
Ende unterliegt es immer deiner Einschätzung, welcher Text erfasst wird. Findest du eine News, die du für wichtig oder
erwähnenswert hältst, kannst du diese gerne erfassen.

## Über Verknüpfungen { .fs-3 }

- Verknüpfungen gehen in beide Richtungen
- Änderungen an einem Teil der Verknüpfung wirken sich auf den anderen Teil aus
- Vorsicht beim Ändern!

## Formularfelder { .fs-3 }

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

### Anmerkungen zu Ort, Spielort, Veranstaltung { .fs-5 }

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
 
