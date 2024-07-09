Aktion
======


Mit Aktionen können mehrere Datensätze gleichzeitig bearbeiten werden.
 Ihr wählt aus dem
 [Dropdown-Menü](bedienelement.md#Einfaches_Auswahlfeld.2FDrop-Down "Bedienelement") die gewünschte Aktion, markiert die zu bearbeitenden Datensätze mithilfe der Checkboxen und klickt dann auf den "Ausführen" Knopf neben dem Dropdown-Menü. Wenn ihr die Checkbox im Spaltenkopf benutzt, werden alle gelisteten Datensätze markiert.







Allgemein stehen die Aktionen "Löschen" und "Zusammenfügen" zur Verfügung. Bei Datensätzen, bei denen Bestandsangaben hinterlegt werden, gibt es zusätzlich die "Bestände ändern" Aktion. Daneben bieten manche Änderungslisten auch noch andere Aktionen für Datensätze ihrer Kategorie an; Erklärungen dazu findet ihr auf der Hilfe-Seite der Kategorie (z.B.
 [Ausgabe#Aktionen](ausgabe.md#Aktionen "Ausgabe")).



### Löschen { .fs-5 }


Hiermit wird die Löschung der ausgewählten Datensätze eingeleitet. Die Datensätze werden zusammen in einem Zug gelöscht. Siehe auch:
 [Löschen](löschen.md "Löschen")



### Bestände bearbeiten { .fs-5 }


Diese Aktion ermöglicht das Bearbeiten der Bestandsangaben von mehreren Datensätzen. Die Bestände der einzelnen Datensätze werden wie aus den
 [Änderungsseiten](oberfläche.md#.C3.84nderungsseite "Oberfläche") gewohnt angezeigt und können frei verändert werden. Änderungen müssen durch einen Klick auf den roten Knopf "Ja, ich in sicher" bestätigt werden, bevor sie übernommen werden.
   




### Zusammenfügen { .fs-5 }


Mit dieser Aktionen können mehrere Datensätze zu einem einzigen Datensatz zusammengefügt werden. Aus den entsprechenden Datensätzen wählt ihr den Datensatz aus, der am Ende des Prozesses übrig bleiben soll. Dieser "primäre Datensatz" wird mit Daten der anderen Datensätze erweitert. Verweise (also z.B. auf Musiker oder Bands, siehe
 [Bedienelement#Inlines](bedienelement.md#Inlines "Bedienelement")) werden immer übernommen, sofern dem primären Datensatz diese Verweise fehlen. Wird bei "Primären Datensatz erweitern" ein Häkchen gesetzt, werden auch Daten, die keine Verweise darstellen und die dem primären Datensatz fehlen, dem primären Datensatzes hinzugefügt.
 Nach dem Erweitern des primären Datensatzes werden die anderen Datensätze gelöscht.



  

**Beispiel:**  

 Die folgenden drei Datensätze sollen zusammengefügt werden, da sie denselben Artikel beschreiben.



Bei der Auswahl des primären Datensatzes werden die Datensätze in derselben Reihenfolge wie in der
 [Änderungsliste](änderungsliste.md "Änderungsliste") dargestellt. Hier soll der oberste Datensatz für dieses Beispiel ausgewählt werden, um das Erweitern der Grunddaten ("Primären Datensatz erweitern") veranschaulichen zu können.



Dem primären Datensatz fehlte eine Zusammenfassung und bei "Primären Datensatz erweitern" wurde ein Häkchen gesetzt: die fehlende Zusammenfassung soll also durch eine Zusammenfassung der anderen Datensätze ersetzt werden. Jedoch haben die beiden anderen Datensätze unterschiedliche Zusammenfassungen - hier muss zunächst eine der beiden Zusammenfassungen ausgewählt werden.



Das Resultat sieht nun so aus:



* nur der primäre Datensatz ist übrig geblieben - die anderen beiden wurden gelöscht
* eine Zusammenfassung wurde hinzugefügt, da sie vorher fehlte
* die Angabe zur Seite wurde **nicht** verändert, da sie vor dem Zusammenfügen bereits existierte
* die Schlagwörter des primären Datensatzes wurden um das Schlagwort ("sekundärer Datensatz") der anderen Datensätze erweitert
* die Künstler des primären Datensatzes wurden um die Künstler der anderen Datensätze erweitert
