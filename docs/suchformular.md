Suchformular
============



[Änderungslisten](%c3%84nderungsliste.md "Änderungsliste") bieten ein Formular an, mit welchem man genauere Parameter (Filter) für eine Suchanfrage an die Datenbank einstellen kann.




 Das Formular enthält ein Feld, mit dem ihr einen Suchbegriff für eine [Volltextsuche](#Textsuche) durchführen könnt.
 Darüber hinaus stellen manche Suchformulare noch mehr Felder zur Verfügung, die mit einem Klick auf "Erweiterte Suchoptionen anzeigen" angezeigt (und auch wieder versteckt) werden können.



Um die Suche zu starten, klickt weiter unten auf den "Suche" Knopf.






 Info
 

Suchparameter werden logisch mit UND verknüpft. Das heisst, ein Datensatz muss alle Suchparameter erfüllen, damit er in der Ergebnisliste auftaucht.


Zum Beispiel: wählt man die Parameter Band "Rolling Stones" und Ort "Dortmund", so wird die Datenbank nach Datensätzen suchen, welche mit den "Rolling Stones" **und** dem Ort "Dortmund" verknüpft sind.
 Erfüllt ein Datensatz nur einen der Parameter (also: entweder "Rolling Stones" oder "Dortmund"), wird er nicht in der Ergebnisliste auftauchen.







### Textsuche { .fs-5 }


Bei der Textsuche werden Textfelder (wie z.B. Schlagzeile, Zusammenfassung oder Beschreibung) der Datensätze nach den Suchbegriffen durchsucht.



 Um auch Datensätze zu finden, die dem Suchbegriff nur ähnlich sind aber nicht exakt entsprechen, werden
 die Texte der Datensätze und die Suchbegriffe zu ihrem [Wortstamm](https://de.wikipedia.org/wiki/Stemming) umgewandelt.
 Die Suche wird dann auf Basis dieser Wortstämme ausgeführt.



So taucht zum Beispiel ein Datensatz mit dem Wort "Arzt" bei einer Suche nach "Die Ärzte" als Ergebnis auf, da "Arzt" und "Ärzte" denselben Wortstamm haben.


## Felder { .fs-3 }


Neben den gewöhnlichen aus den Änderungsformularen bekannten
 [Bedienelementen](bedienelement.md "Bedienelement"), tauchen in Suchformularen auch noch Felder mit Besonderheiten auf.



### von - bis Felder { .fs-5 }



Hiermit kann ein Zahlenbereich von einschließlich X bis einschließlich Y (also: "größer gleich X und kleiner gleich Y") angegeben werden. Wird nur in dem ersten Feld ein Wert eingetragen, so wird stattdessen nach genau diesem Wert gesucht (also: "gleich X").
![von - bis Felder]()

### partielles Datum { .fs-5 }



Ähnlich wie das "von bis Feld", nur mit teilweisen Datumsangaben.
![Partielles Datum]()





### ID { .fs-5 }



Ermöglicht es, Datensätze mittels ihrer
 [ID](id.md "ID")-Nummer zu finden. Mehrere Nummern mit Kommas trennen.
 
![ID Suchfeld]()
