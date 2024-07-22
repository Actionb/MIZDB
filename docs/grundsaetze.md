# Grundsätze

Für die Arbeit an der Datenbank gelten folgende grobe Richtlinien:

## Korrektheit der Angaben prüfen

[comment]: <> (@formatter:off)  
!!! tip "Es ist wichtig, dass man sich auf die Korrektheit der Informationen in der Datenbank verlassen kann"
    Bist du dir bei etwas nicht völlig sicher, informiere dich erst einmal weiter oder frage bei anderen nach.
  
[comment]: <> (@formatter:on)

Trifft man beim Recherchieren mit der Datenbank auf falsche Informationen, dann wird das Vertrauen in die Datenbank
insgesamt getrübt - schließlich könnten andere Angaben auch falsch sein. Bevor du also Informationen in die Datenbank
einfügst, oder Angaben in der Datenbank änderst, sei dir absolut sicher, dass die Angaben, die du machst, korrekt sind.
Im Zweifelsfall lässt du die Angaben oder Informationen eher weg. Dies geht auch in den nächsten Grundsatz über:

## Nahe am Material arbeiten

[comment]: <> (@formatter:off)  
!!! tip "Dinge nur genauso eintragen, wie sie da stehen"  
    Das heißt: nichts erfinden, nichts hineininterpretieren! 
  
[comment]: <> (@formatter:on)

Formularfelder leer zu lassen ist okay. Gibt das zu erfassende Archivmaterial keine Informationen zu einem Feld her,
dann darf auch nichts eingetragen werden. Fehlt beispielsweise einer Ausgabe eine Monatsangabe, so darfst du eine solche
Angabe nicht erfinden oder von der Ausgabennummer ableiten.

Auch solltest du nicht deine persönliche Interpretation zu dem Material einfügen. Wenn du einen Zeitschriftenartikel
erfasst, ist es nicht deine Aufgabe ihn zu interpretieren, sondern lediglich die Informationen aus dem Artikel in die
Datenbank einzutragen.

## Datensätze müssen aufschlussreich sein

[comment]: <> (@formatter:off)  
!!! tip "Ein Datensatz ohne Informationen hilft niemanden"
    Wenn du keinen aufschlussreichen Datensatz erstellen kannst, dann lasse es bleiben.
  
[comment]: <> (@formatter:on)

Ein Datensatz ist nur dann nützlich, wenn man den Kontext um diesen Datensatz erkennen kann; wenn man versteht, wer oder
was mit dem Datensatz gemeint ist. Dazu ist es notwendig, dass der Datensatz genügend Informationen enthält.

Die Anforderungen für einen minimalen Datensatz sind in der MIZDB sehr gering. So musst du meistens nur ein einziges
Feld ausfüllen, bevor du den Datensatz abspeichern darfst. Allerdings ist diese eine Angabe alleine in vielen Fällen
nicht aussagekräftig genug. Es liegt also an dir, weitere Informationen zu hinterlegen, wenn du einen Datensatz
erstellst, damit andere verstehen können, was mit dem Datensatz gemeint ist.

Beispiel: wenn du einen Personen-Datensatz mit Vorname "A." und Nachname "B." erstellst, dann ist es praktisch
unmöglich, anhand des Datensatzes zu erkennen, welche Person damit gemeint ist. Der Datensatz ist somit ziemlich
nutzlos.

## So viel Informationen wie nötig (und so wenig wie möglich)

[comment]: <> (@formatter:off)  
!!! tip "Die Datenbank soll kein Lexikon sein"
    Du musst nicht die gesamte Geschichte einer Band in die Datenbank abbilden. Du musst nur genügend Informationen
    hinterlegen, damit die Band und Archivmaterialien zu dieser Band gefunden werden können.
  
[comment]: <> (@formatter:on)

Bei einer Suche wird der Suchbegriff mit den Angaben des Datensatzes verglichen. Das bedeutet, dass deine Angaben zum
"Wiederfinden" eines Datensatzes beitragen. Besitzt ein Datensatz kaum bis keine Angaben, so kann er auch kaum bis gar
nicht gefunden werden. Je mehr Angaben ein Datensatz besitzt, um so leichter ist es, diesen Datensatz wiederzufinden,
weil eine größere Auswahl an Suchbegriffen zum Datensatz führen würden.

Es wäre also erst einmal ideal, zu jedem Datensatz möglichst viele Angaben zu machen. Leider gibt es bei der Erfassung
von Daten aber auch eine zeitliche Komponente: wenn du für die Erfassung der Artikel einer Zeitschrift mehrere Wochen
brauchst, weil du extrem detailliert arbeitest, dann kannst du insgesamt weniger Artikel erfassen. Demnach ist eine
ausgewogene Detailverliebtheit wünschenswert: so viel wie nötig, aber so wenig wie möglich.

Beispiel: werden in einem Artikel die Mitglieder einer Band besprochen, so ist es sinnvoll bei der Band diese Mitglieder
auch anzugeben. Damit könnte der Artikel über den Datensatz eines Bandmitglieds gefunden werden. Dagegen wäre eine
Auflistung aller Mitglieder, die je an der Band beteiligt gewesen waren, unnötig viel Arbeit.

## Nicht an Datenbank-Limitierungen vorbeiarbeiten

[comment]: <> (@formatter:off)  
!!! tip "Die Datenbank meckert nur aus gutem Grund"
    Wenn die Datenbank meckert und einen Fehler anzeigt, dann geschieht dies (meistens) aus gutem Grund: gemachte Angaben
    könnten problematisch, unzureichend oder fehlerhaft sein.
  
[comment]: <> (@formatter:on)

Beispiel: du willst einen Personen-Datensatz erstellen, obwohl du nur den Vornamen der Person kennst. Die Datenbank
lässt dies aber nicht zu, denn eine Angabe zum Nachnamen ist zwingend erforderlich. Um den Datensatz doch noch
abspeichern zu können, könntest du den Vornamen in das Feld für den Nachnamen eintragen.
Dies wäre jedoch falsch, denn eine Angabe zum Nachnamen ist nötig, um von den Daten des Datensatzes auf eine
tatsächliche Person schließen zu können. Umgehst du diese Limitierung, macht der Datensatz insgesamt also wenig Sinn
(siehe [Datensätze müssen aufschlussreich sein](#datensatze-mussen-aufschlussreich-sein)).

## Als Nächstes

* [Artikel erfassen](erfassung.md)
