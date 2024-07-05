Löschen
=======


Beim Löschen wird der jeweilige
 [Datensatz](datensatz.md "Datensatz") aus der Datenbank entfernt. 


 Eine Wiederherstellung ist nicht möglich. Verweise von anderen Datensätzen auf diesen gelöschten Datensatz werden ebenfalls entfernt: löscht man ein Genre, so wird auch bei jedem Musiker der Verweis auf jenes Genre gelöscht.



Alle von der Löschung betroffenen Objekte und Verweise (Beziehungen) werden in der Zusammenfassung auf der Seite, die die Löschung einleitet, aufgelistet.



### Geschützte Objekte


Manche Datensätze können nur unter bestimmten Umständen gelöscht werden. Versucht man, einen Datensatz mit geschützten Objekten zu löschen, so warnt die Datenbank:




```
Kann Ausgabe nicht löschen
Das Löschen von Ausgabe „2000-1“ würde ein Löschen der folgenden geschützten verwandte Objekte erfordern: Artikel: Testartikel

```

Um das zu erklären, hier eine Beispiel mit [Artikeln](artikel.md "Artikel") und
 [Ausgaben](ausgabe.md "Ausgabe"):



Ein Artikel erfordert immer eine Angabe zu der Ausgabe einer Zeitschrift, aus der der Artikel stammt. Dementsprechend ist Ausgabe ein notwendig erforderliches Feld (das nicht leer bleiben darf) für jeden Datensatz eines Artikels.



Wird die Ausgabe eines Artikels gelöscht, würde auch der Verweis auf die Ausgabe aus dem Datensatz des Artikels verschwinden; das Feld Ausgabe würde für den Artikel leer bleiben - dies ist aber nicht erlaubt ([Referentielle Integrität](https://en.wikipedia.org/wiki/de:Referentielle_Integrit%C3%A4t "wikipedia:de:Referentielle Integrität")).



Die Datenbank würde dieses Beziehungsproblem dadurch lösen, dass sie
 **den Artikel ebenfalls löscht**. In manchen Fällen ist dieses Verhalten durchaus erwünscht. Bei Ausgaben könnte dies jedoch zur Löschung von vielen Artikeln auf einen Schlag führen.
 Um eine Löschung mit drastischen Folgen vorzubeugen, ist die Löschung von manchen Arten von Datensätzen (Ausgaben, Magazine) nur dann erlaubt, wenn es keine verwandten Datensätzen gibt, die von dem zu löschenden Datensatz abhängig sind und dementsprechend dann ebenfalls gelöscht werden würden.



Die Beziehung von Artikel zu Ausgabe gilt als geschützt: eine Ausgabe *ohne* Artikel kann gelöscht werden. Eine
 *mit* Artikeln jedoch nicht.


