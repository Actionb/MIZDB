
import re
import xml.etree.ElementTree as et

from DBentry.models import *
from DBentry.helper import *
   
   
def split_MuBa():
    # TODO: Exclude Mr./Mister/Mrs./etc?
    x = 'ExportData/musikerbands.xml'
    splitlog = open('ExportData/logs/MuBa_splitlog.txt', 'w')
    tree = et.parse(x)
    elements = tree.findall('artist')
    musiker = et.ElementTree(element = et.Element('dataroot'))
    bands = et.ElementTree(element = et.Element('dataroot'))
    for e in elements:
        if e.findtext('ist_band') == '-1':
            if not e.findtext('vorname') and not e.findtext('nachname'):
                if len(e.findtext('artist_name').split())==1:
                    # artist_name is single 'name'
                    v = None
                    n = None
                else:
                    # Remove "X" artistic names
                    name = e.findtext('artist_name')
                    regex = re.search(r'(".*")', name)
                    if regex:
                        name = name.replace(regex.group(), '')
                    # Split name into vorname, nachname (helper.py)
                    v, n = split_name(name)
                if v:
                    vorname = et.Element('vorname')
                    vorname.text = v
                    e.append(vorname)
                if n:
                    nachname = et.Element('nachname')
                    nachname.text = n
                    e.append(nachname)
            
            musiker.getroot().append(e)
            print("Added musiker {}, Vorname: {}, Nachname: {}.".format(
                    e.findtext('artist_name'), 
                    e.findtext('vorname'), 
                    e.findtext('nachname'), 
                    ),  file=splitlog
                )
        else:
            if e.findtext('ist_band') == '0':
                print(e.findtext('artist_name'))
            if e.findtext('ist_band') != '-2':
                bands.getroot().append(e)
    splitlog.close()
    musiker.write('ExportData/musiker.xml')
    bands.write('ExportData/bands.xml')

    
    
class MIZReader(object):
    
    tag_dict = {
       
        # Artikel
        artikel : {
            'topic' : 'zusammenfassung', 
            'issue_ID' : 'ausgabe_id', 
            'headline' : 'schlagzeile', 
            'page' : 'seite',
            'nrpages' : 'seitenumfang', 
            'info' : 'info', 
        }, 
        artikel.genre.through : {
            'article_ID' : 'artikel_id', 
            'genre_ID' : 'genre_id', 
        }, 
        artikel.schlagwort.through : {
            'article_ID' : 'artikel_id', 
            'type_ID' : 'schlagwort_id', 
        }, 
        artikel.autor.through : {
            'article_ID' : 'artikel_id', 
            'author_ID' : 'autor_id', 
        }, 
        artikel.musiker.through : {
            'article_ID' : 'artikel_id', 
            'artist_ID' : 'musiker_id', 
        }, 
        artikel.band.through : {
            'article_ID' : 'artikel_id', 
            'artist_ID' : 'band_id', 
        }, 
        
        # Ausgabe
        ausgabe : {
            'info' : 'info', 
            'journal_ID' : 'magazin_id', 
            'status' : 'status', 
            'issue_date' : 'e_datum', 
        }, 
        
        ausgabe_jahr : {
            'issue_year' : 'jahr1', 
            'issue_year2' : 'jahr2', 
            'issue_year3' : 'jahr3', 
            'ID' : 'ausgabe_id', 
        }, 
        
        ausgabe_num  : {
            'issue_name' : 'num1',
            'issue_name2' : 'num2',
            'issue_name3' : 'num3',
            'ID' : 'ausgabe_id', 
        }, 
        
        ausgabe_lnum : {
            'lnum' : 'lnum1',
            'lnum2' : 'lnum2',
            'ID' : 'ausgabe_id', 
        }, 
        
        ausgabe_monat : {
            'month1' : 'monat_id1', 
            'month2' : 'monat_id2', 
            'month3' : 'monat_id3', 
            'ID' : 'ausgabe_id', 
        }, 
        
        # Autor
        autor : {
            'author_pre' : 'vorname', 
            'author_sur' : 'nachname', 
            'alias' : 'kuerzel', 
            #'journal_ID' : 'magazin', 
        }, 
        autor.magazin.through: {
            'ID' : 'autor_id', 
            'journal_ID' : 'magazin_id', 
        }, 
        
        # Band
        band : {
            'artist_name' : 'band_name', 
            'origin_ID' : 'herkunft_id', 
            #'mitglieder' : 'mitglieder', 
            'beschreibung' : 'beschreibung', 
        }, 
        band_alias : {
            'alias' : 'alias', 
            'ID' : 'parent_id'
        },
        band.musiker.through : {
            'ID' : 'band_id', 
            'mitglieder' : 'musiker', 
        }, 
        band.genre.through : {
            'artist_ID' : 'band_id', 
            'genre_ID' : 'genre_id', 
        }, 
         
        # Bundesland
        bundesland : {
            'state_name' : 'bland_name', 
            'state_code' : 'code', 
            'country_ID' : 'land_id', 
        }, 
        
        # Genre
        genre : {
            'genre_name' : 'genre', 
            'main_genre' : 'ober_id', 
        }, 
        genre_alias : {
            'alias' : 'alias', 
            'ID' : 'parent_id', 
        }, 
    
        # Land
        land : {
            'country_name' : 'land_name', 
            'country_code' : 'code', 
        }, 
        
        # Magazin
        magazin : {
            'journal_name' : 'magazin_name',
            'first_issue' : 'erstausgabe', 
            'interval' : 'turnus', 
            'publisher' : 'verlag_id', 
            'URL' : 'magazin_url', 
            'origin_ID' : 'ort_id', 
            'description' : 'beschreibung', 
            'country_ID' : 'country_id', 
        }, 
        magazin.genre.through : {
            'journal_ID' : 'magazin_id', 
            'genre_ID' : 'genre_id',         
        }, 
        
        # Musiker
        musiker : {
            'artist_name' : 'kuenstler_name', 
            'vorname' : 'vorname', 
            'nachname' : 'nachname', 
            'origin_ID' : 'herkunft_id', 
            'beschreibung' : 'beschreibung', 
            'mitglieder' : 'mitglieder', 
        }, 
        musiker_alias : {
            'alias' : 'alias', 
            'ID' : 'parent_id'
        }, 
        musiker.genre.through : {
            'genre_ID' : 'genre_id', 
            'artist_ID' : 'musiker_id', 
        }, 
        
        # Schlagwort
        schlagwort : {
            'type_name' : 'schlagwort', 
            'main_type' : 'ober_id', 
        }, 
        schlagwort_alias : {
            'alias' : 'alias', 
            'ID' : 'parent_id', 
        }, 
        
        # Ort
        ort : {
            'state_ID' : 'bland_id', 
            'country_ID' : 'land_id', 
            'originstring' : 'stadt', 
        }, 
        
        person : {
            'author_pre' : 'vorname', 
            'author_sur' : 'nachname', 
            'vorname' : 'vorname', 
            'nachname' : 'nachname', 
            'origin_ID' : 'herkunft_id', 
            #'ID' : 'original_id', 
        }, 
        
        provenienz : {
            'provenance' : 'geber', 
            'entry_type' : 'typ', 
        }, 
        
        verlag : {
            'publisher' : 'verlag_name', 
        }, 
    }
    
    def __init__(self, instance, tag = None):
        self.instance = instance
        if tag:
            self.tag_dict = tag
            
    def get_tag_set(self):
        # Return all tags used by the .xml source
        tree = et.parse(self.instance.source)
        elements = tree.findall(self.instance.root)
        tags = set()
        for elem in elements:
            items = list(elem)
            for i in items:
                tags.add(i.tag)
        return tags
            
    def read(self, convert_tags = True):
        tree = et.parse(self.instance.source)
        elements = tree.findall(self.instance.root)
        for elem in elements:
            items = list(elem)
            if convert_tags:
                content = {}
                for i in items:
                    if i.text and i.text != '0':
                        tag = self.convert_tag(i.tag)
                        if tag:
                            content[tag] = i.text.strip()
                        else:
                            # No fitting tag found, current item is excluded from result
                            pass
                            
                if self.instance.model:
                    # I fucked up the splittig of MuBa, having lotsa 'nachname:unbekannt' in the data screws up the Importer clean_row bits
                    if self.instance.source.endswith('musiker.xml') and self.instance.model == musiker:
                        if 'nachname' in content.keys() and content['nachname'] == 'unbekannt':
                            del content['nachname']
                    
                    
                    # Wir müssen die verschiedenen Angaben (Jahr,Num,Lnum,Monat) zu Ausgaben auseinander fummeln
                    if self.instance.source.endswith('issue.xml') and self.instance.model != ausgabe:
                        for k, v in content.items():
                            if k != 'ausgabe_id':
                                yield {k[:-1]:v.strip(), 'ausgabe_id' : content['ausgabe_id']}
                        continue
                        
                    # Aliase wurden nur mit Kommata getrennt, wir müssen diese in einzelne Datensätze aufteilen
                    if self.instance.model.__name__.endswith('_alias') and 'alias' in content:
                        for alias in content['alias'].split(","):
                            if len(alias.strip())>1:
                                yield {'alias':alias.strip(), 'parent_id':content['parent_id']}
                        continue
                        
                    # Band-Mitglieder aufteilen und zur Erstellung bereitstellen.
                    # Wir erstellen erst alle Mitglieder als Musiker und teilen diese später den Bands zu.
                    if self.instance.model == musiker and self.instance.source.endswith('bands.xml'):
                        if 'mitglieder' in content.keys():
                            for m in content['mitglieder'].split(","):
                                if m.strip():
                                    yield {'kuenstler_name':m.strip()}
                            continue
                        else:
                            continue
                    
                    if self.instance.model == band.mitglieder.through and self.instance.source.endswith('bands.xml'):
                        if 'mitglieder' in content.keys() and 'band_id' in content.keys():
                            for m in content['mitglieder'].split(","):
                                if m.strip():
                                    yield {'band_id':content['band_id'],'musiker_id':m.strip()}
                            continue
                        else:
                            continue
                        
                    # Manche Artikel haben keine Seitenangabe
                    if self.instance.model == artikel:
                        if 'seite' not in content.keys() and len(content.keys())>1:
                            content['seite'] = -1
                        
                    # Stadt-Namen anpassen
                    if self.instance.model == ort:
                        if 'stadt' in content.keys():
                            i = content['stadt']
                            stadt_name = i.text[:i.text.find(',')] if ',' in i.text else i.text
                            content['stadt'] = stadt_name.strip()
    
            else:
                # i.text.strip() if i.text else i.text  bedeutet: wenn i.text gleich None oder '' -> i.text ansonsten i.text.strip()
                content = {i.tag: i.text.strip() if i.text else i.text for i in items} 
            
            if not content:
                continue
                
            # NOTE: may filter out necessary data, keep an eye on it
            if len(content) == 1 and list(content.keys())[0].lower() != 'id':
                # content consists only of an ID record, useless and skip
                continue
                
                
            yield content
            
    def search(self, to_find = [], tags = [],  ignore_alias = True):
        # NOTE: Nur für get_musiker und get_bands benutzt?
        keywords = [' the ', ' and ', ' or ']
        rslt = []
        if not to_find:
            return rslt
        if not tags:
            tags = self.get_tag_set()
            if 'alias' in tags and ignore_alias:
                tags.remove('alias')
        if isinstance(to_find, str):
            to_find = to_find.split()
        tree = et.parse(self.instance.source)
        elements = tree.findall(self.instance.root)
        for elem in elements:
            items = list(elem)
            match = False
            for i in items:
                if i.tag in tags:
                    if isinstance(i.text, str):
                        for f in to_find:
                            if re.search(r'\b{}\b'.format(f.replace('.', '')), i.text, re.IGNORECASE):
                                match = True
                                break
            if match:
                rslt.append({i.tag:i.text for i in items})
        return rslt
        
    
    def convert_tag(self, tag):
        """
        Return instance.model field name as XML tag replacement from the tag_dict.
        Return None if the content of that element is not included in the tag_dict.
        """
        if self.instance.model in self.tag_dict:
            if tag in self.tag_dict[self.instance.model]:
                return self.tag_dict[self.instance.model][tag]
            elif tag == 'ID':
                return 'id'
            else:
                return None
        return tag
        

import csv
class CSVReader(object):
    
    def __init__(self, file_path = None, file = None, tags = {}, reader = csv.DictReader):
        self.file = file or open(file_path) 
        self.reader = reader
        
        if isinstance(tags, (list, tuple)):
            tags = {tags[0]:tags[0]}
        if isinstance(tags, str):
            tags = {tags:tags}
        self.tags = tags
        
    def get_reader(self):
        self.file.seek(0)
        return self.reader(self.file)
    
    def read(self):
        for row in self.get_reader():
            if self.tags:
                return_row = {}
                for k, v in row.items():
                    if k in self.tags:
                        return_row[self.tags[k]] = v
                yield return_row
            else:
                yield row
                
    def print_rows(self, row_number = 0, to_file = None):
        for c, row in enumerate(self.read(), 2):
            if c == row_number:
                break
            print(row, file=to_file)
            
    def print_row(self, row_number = 0, to_file = None):
        if not row_number:
            return
        for c, row in enumerate(self.read(), 2):
            if c == row_number:
                print(row, file=to_file)
                break
