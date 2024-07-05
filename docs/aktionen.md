Aktionen
========


Auf der Seite der Änderungsliste könnt ihr
 [Datensätze](datensatz.md "Datensatz") durchsuchen und ändern. 


 Um beispielsweise zur Änderungsliste der Artikel-Datensätze zu gelangen, klickt ihr auf der
 [Indexseite](oberfl%c3%a4che.md#Index "Oberfläche") entweder auf den Link mit der Beschriftung "Artikel" oder auf den "Ändern" Knopf daneben. Der obere Teil der Seite dient der Eingabe von Suchparametern bzw. dem Setzen von Filtern (siehe
 [Suchformular](suchformular.md "Suchformular")). Darunter, direkt über der Tabelle, befindet sich das
 [Auswahlfeld](bedienelement.md#Einfaches_Auswahlfeld.2FDrop-Down "Bedienelement") für die
 [Aktionen](aktion.md "Aktion") und der Knopf, der Ausführung der ausgewählten Aktion einleitet.



Darauf folgt die Tabelle, die die Suchergebnisse darstellt. Die erste, unbeschriftete Spalte stellt Auswahlkasten ([Checkboxes](https://en.wikipedia.org/wiki/de:Checkbox "wikipedia:de:Checkbox")) zur Verfügung, mit welchen man Datensätze für Aktionen auswählen kann, mehr dazu hier:
 [Aktionen](aktion.md "Aktion").
 Danach kommen beschriftete Spalten, in denen Daten der gefundenen Ergebnisse angezeigt werden, um einen Überblick über den Inhalt der Datensätze zu ermöglichen.



### Sortierung


Die Ergebnisse werden stets sortiert dargestellt. Die Spalten, nach denen sortiert wird, erkennt man an einem kleinen dreieckigen Symbol am rechten Rand im Spaltenkopf. Zeigt das Dreieck nach oben, werden die Werte der Spalte aufsteigend sortiert (kleinste Werte nach oben). Zeigt es nach unten, wird absteigend sortiert (größte Werte nach oben). Durch einen Klick auf das Dreieck könnt ihr zwischen auf- und absteigend wechseln.




**Wichtig**: Zahlenfelder werden nach ihrem Zahlenwert sortiert, Textfelder werden jedoch lexikographisch sortiert (siehe
 [Wikipedia: Lexikographische Ordnung](https://en.wikipedia.org/wiki/de:Lexikographische_Ordnung "wikipedia:de:Lexikographische Ordnung")). Demnach würden
 *Zahlenwerte in Textfeldern* ebenfalls lexikographisch sortiert werden: der Wert
 `"10"` würde vor dem Wert
 `"2"` eingeordnet werden, da das erste Zeichen des ersten Wertes (`1`) kleiner ist als das erste Zeichen des zweiten Wertes (`2`). Wäre der zweiten Wert hingegen
 `"02"`, so wäre die Ordnung wie erwartet: `"02"` käme vor `"10"`.
 Ein Beispiel für eine scheinbar unpassende Sortierung wegen lexikographischer Ordnung ist die Sortierung der Artikel nach Ausgaben: siehe
 [Ausgabe#Sortierung](ausgabe.md#Sortierung "Ausgabe").



Wird nach mehreren Spalten sortiert, so wird die Reihenfolge der Sortierung durch Ziffern neben dem Dreieck wiedergegeben. Beispiel: Artikel (siehe Bild oben) werden zuerst nach Magazin, dann nach Ausgaben, dann nach Seitenzahl und schließlich nach Schlagzeile sortiert. Das bedeutet, dass zuerst alle Artikel nach Magazinen gruppiert und sortiert werden. Dann werden alle Artikel desselben Magazins nach Ausgabe sortiert. Dann alle Artikel derselben Ausgabe nach Seite. Und so weiter.



Wenn ihr auf eine Spalte klickt, so wird primär nach dieser Spalte sortiert: sie wird in der Spaltenordnung an die erste Stelle gesetzt.
 Um die Sortierung nach einer Spalte aufzuheben, klickt auf das kleine Symbol, das erscheint, wenn ihr die Maus über die Spalte bewegt:



.



  

 Wollt ihr die voreingestellte Sortierung wiederherstellen, dann klickt auf den Link mit der Beschriftung "Sortierung zurücksetzen". Dieser erscheint sich zwischen der Textsuche und dem Bereich für Aktionen, sobald die Sortierung geändert wurde.







### Ungefilterte Liste anzeigen


Manche Änderungslisten sind zunächst leer und zeigen keine Ergebnisse an, um den Seitenaufbau zu beschleunigen, und um
 [*ungefilterte* Anfragen](suchformular.md "Suchformular") an die Datenbank zu vermeiden.
 Eine ungefilterte Liste kann angefordert werden, indem man auf den Link "insgesamt" neben der Ergebniszahl klickt:







### Paginierung aufheben


Standardmäßig wird die Ergebnisliste in Seiten unterteilt ([Paginierung](https://en.wikipedia.org/wiki/de:Paginierung#Paginierung_in_der_Suchmaschinenoptimierung "wikipedia:de:Paginierung")). Um alle Ergebnisse gleichzeitig aufzulisten, kann die Paginierung durch einen Klick auf den "Zeige alle" Link aufgehoben werden:






