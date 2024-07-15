Erfassung von Artikeln
=======



Die Erfassung der Zeitungsartikel ist recht unkompliziert und ist damit gut für Anfänger als Einleitung in die Datenbank
geeignet.

## Erfassung

Bei der Erfassung ist es deine Aufgabe, die wichtigsten Informationen, die in einem Artikel enthalten sind, in die
Datenbank einzufügen, sodass der Artikel bei einer Suche wiedergefunden werden kann.

Für ein Beispiel nehmen wir mal an, dass du einen Artikel aus einem Heft des "Rolling Stone" Magazins erfassen willst.
Um mit der Erfassung zu beginnen, solltest du zuerst die Datenbank nach vorhandenen Artikel dieses Heftes durchsuchen.

### Vorhandene Artikel suchen

Bevor du einen neuen Artikel hinzufügst, solltest du erst schauen, ob dieser schon in der Datenbank existiert.
Ist der Artikel bereits erfasst, solltest du ihn nicht noch einmal eintragen.

So suchst du nach den Artikeln eines Heftes:

1. im [Index/Hauptmenü](oberflaeche.md#Index "Oberfläche") auf "Artikel" klicken
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

[comment]: <> (@formatter:off)
!!! tip "Tip: Praktisch"
    Durch die Suche werden die Angaben zu **Magazin** und **Ausgabe** im Suchformular an die Formulare für neue Artikel
    weitergereicht und dort in die entsprechenden Felder automatisch eingefügt. Dadurch ersparst du dir etwas Arbeit.

[comment]: <> (@formatter:on)

### Neuen Artikel erstellen

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
die [Suche](#vorhandene-artikel-suchen) gemacht hast) und die **Schlagzeile** ein.

Je nach Artikel ist es manchmal nicht ganz klar, was die Schlagzeile eines Artikels ist. Lasse dich davon nicht
entmutigen; die Schlagzeile dient schlicht als Erkennungsmerkmal und ist inhaltlich nicht so sehr wichtig.
Trage also das ein, was du als Schlagzeile erachtest. Oder schaue im Inhaltsverzeichnis der Ausgabe nach, was dort als
Titel angegeben ist.

Anschließend musst du die **Seite**, an der der Artikel beginnt, und den **Seitenumfang** eintragen. Ist der Artikel nur
eine Seite lang, musst du bei **Seitenumfang** nichts angeben.

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

[comment]: <> (@formatter:off)
!!! caution "Achtung: Abspeichern ist notwendig!"
    Änderungen werden nur übernommen, wenn du auf einen der "[Sichern](sichern.md "Sichern")" Knöpfe klickst.
    Verlässt du das Formular (z.B. indem du das Fenster schließt oder zu einer anderen Seite navigierst), ohne es zu
    sichern, geht deine Arbeit verloren!
    Es sollte eine Warnung auftauchen, wenn du versuchst, ein Formular mit ungespeicherten Änderungen zu verlassen.

[comment]: <> (@formatter:on)

### Artikel Inhalt aufnehmen

Bisher hast du nur Angaben zu dem Heft, der Schlagzeile und der Seitenzahl gemacht. Das ist aber noch nicht
aussagekräftig genug, denn über den Inhalt des Artikels hast du noch keine Angaben gemacht.
Also ist es jetzt an der Zeit, dass du dir den Artikel einmal durchliest. Anschließend solltest du eine
Zusammenfassung des Artikels in das entsprechende Feld des Formulars eintragen.

Anhand der Zusammenfassung werden Recherchierende feststellen können, ob der Artikel für sie interessant ist oder nicht.
Dementsprechend solltest du dir hier Mühe geben, die relevanten Teile eines Artikels anzugeben. Dabei ist es wichtiger,
dass alle wichtigen, interessanten Informationen enthalten sind, als dass du einen schönen Text schreibst. Wenn es dir
leichter fällt, kannst du anstelle von Fließtext auch Stichpunkte benutzen. Die Hauptsache ist, dass die Informationen
in die Datenbank übertragen werden. Die Zusammenfassung wird in die Volltextsuche miteinbezogen; d.h. ein Artikel kann
anhand der Angaben in der Zusammenfassung wiedergefunden werden.

[comment]: <> (@formatter:off)  
!!! info "Info: Nur Relevantes eintragen"
    Machst du keine Angaben, kann der Artikel auch nie gefunden werden. Machst du hingegen viele ungenaue oder 
    überflüssige Angaben, so kann der Artikel unerwünscht als Ergebnis auftauchen. Trage also nur das ein, was für den
    Artikel relevant ist, oder was für das Thema des Artikels von Bedeutung ist.<br>  
    **Beispiel**: Wird in einem Artikel eine Band nur beiläufig erwähnt, so solltest du diese Band nicht erwähnen.

[comment]: <> (@formatter:on)

[comment]: <> (@formatter:off)  
!!! tip "Tip: Textfeld zu klein?"  
    Manche Textfelder, wie z.B. "Zusammenfassung", kannst du vergrößern oder verkleinern, in dem du im Textfeld unten 
    rechts auf das kleine Symbol klickst, die Maustaste gedrückt hältst und dann die Maus rauf- oder runterbewegst. 

[comment]: <> (@formatter:on)

### Verknüpfungen hinzufügen

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

[comment]: <> (@formatter:off)  
!!! warning "Wichtig: Ausreichend Angaben machen"  
    Wenn du eine neue Band erstellst, solltest du mehr Informationen als nur den Namen hinterlegen. Es kommt häufig vor, 
    dass zwei Bands denselben Namen haben. Um diese voneinander unterscheiden zu können, solltest du weitere Angaben wie
    zum Beispiel Genres, Aliase oder Links zu Wikipedia oder Discogs machen. Dies gilt [grundsätzlich](grundsaetze.md) 
    für alle Arten von Datensätzen.<br>  
    Hast du für die Erstellung den "Hinzufügen" Knopf des Dropdown-Menüs benutzt, kannst du auf den Bleistift neben der
    erstellten Band klicken, um zu der Änderungsseite zu gelangen.
    
[comment]: <> (@formatter:on)

[comment]: <> (@formatter:off)
!!! warning "Wichtig: Duplikate vermeiden"
    Grundsätzlich solltest du es vermeiden, Duplikate zu erstellen; ist zum Beispiel eine Band bereits in der Datenbank 
    eingetragen, so solltest du nicht eine weitere Band mit demselben Namen hinzufügen (es sei denn es ist eine komplett
    andere Band, die den denselben Namen hat).

[comment]: <> (@formatter:on)

### Bearbeitung abschließen

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

[comment]: <> (@formatter:off)  
!!! tip "Tip: Welchen Knopf soll ich benutzen?"  
    Der "**Sichern und neu hinzufügen**" Knopf bietet sich an, wenn du mit der Erfassung eines Objekts fertig geworden bist
    und direkt mit der Erfassung des nächsten Objekts anfangen möchtest.  
    Wenn du dabei bist, von der Übersichtsseite aus einige Datensätze zu ändern, dann benutze den "**Sichern**" Knopf, um
    sofort wieder zu der Übersichtsseite zurückzukehren.  
    "**Sichern und weiterbearbeiten**" kannst du während der Erfassung immer wieder mal benutzen, um deine Arbeit 
    abzuspeichern.
  
[comment]: <> (@formatter:on)

## Welche Artikel müssen erfasst werden und welche nicht?

Prinzipiell kann jeder Text einer Ausgabe erfasst und eingetragen werden. Jedoch haben manche Abschnitte wenig
Informationsgehalt: News mit einem Umfang von 20 Wörtern haben meist nicht viel Aussagekraft. Aus Zeitgründen ist die
Richtlinie daher, dass nur echte Artikel erfasst werden *müssen* und andere Texte eher nicht erfasst werden *sollten.*
Ein "echter Artikel" wäre z.B. etwas, das im Inhaltsverzeichnis erwähnt wird, eine Autorenangabe hat oder etwas, das
über einen gewissen Umfang verfügt. "Andere Texte" wären dann News oder Rezensionen von Veröffentlichungen (also z.B.
Reviews von Musikalben). Ob etwas Informationsgehalt hat, bemerkst du dann, wenn du die Zusammenfassung schreiben
willst: fällt die Zusammenfassung sehr dünn aus, ist das ein Indiz dafür, dass du den Text nicht aufnehmen brauchst. Am
Ende unterliegt es immer deiner Einschätzung, welcher Text erfasst wird. Findest du eine News, die du für wichtig oder
erwähnenswert hältst, kannst du diese gerne erfassen.

[comment]: <> (@formatter:off)  
!!! info "Info: Zeit"  
    Du stehst hier nicht unter Zeitdruck. Allerdings ist es sinnvoller, mehr Zeit mit der Erfassung von "echten Artikeln"
    zu verbringen als mit der Erfassung von kleinen News-Schnipseln oder Rezensionen, die mehr Werbung als interessanter
    Text sind.
  
[comment]: <> (@formatter:on)

### Ein Kompromiss, um Rezensionen trotzdem aufzunehmen

In Rezensionen können auch Künstler oder Bands erwähnt sein, die zu klein oder zu unbekannt für einen vollständigen
Artikel sind. Wenn Rezensionen also nicht erfasst werden, dann existiert in der Datenbank auch kein Hinweis auf
einen Künstler, der nur in einer Rezension aufgetaucht ist. Als Kompromiss bietet es sich hier an, anstatt einem
Artikel für jede einzelne Rezension nur einen einzigen Artikel für *alle* Rezensionen einer Ausgabe zu erstellen. Das
spart Zeit und erzeugt trotzdem Hinweise auf die erwähnten Künstler.

Als Schlagzeile nimmst du zum Beispiel einfach den Namen der Rubrik mit den Rezensionen. In der Zusammenfassung trägst
du nun die Namen der Künstler/Bands ein und die Namen der Alben/der Singles. Natürlich kannst du auch explizite
Verknüpfungen zu den Musikern oder Bands hinzufügen - denke aber daran, hier nicht zu viel Zeit zu verbringen.

So wird in der Zusammenfassung der Künstler namentlich erwähnt und damit besteht in der Datenbank auch ein Hinweis auf
diesen Künstler.

<div markdown class="d-flex justify-content-evenly gap-5 text-center">  
<figure markdown="span">  
  ![Beispiel: Rezension](img/artikel_rezension.png){ width="300" .mb-1 }  
  <figcaption>Beispiel: Rezension</figcaption>  
</figure>
</div>

## Über Verknüpfungen

- Verknüpfungen gehen in beide Richtungen
- Änderungen an einem Teil der Verknüpfung wirken sich auf den anderen Teil aus
- Vorsicht beim Ändern!