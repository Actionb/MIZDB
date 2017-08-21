
from django.db import models

class m2mBase(models.Model):
                
    exclude = []
    def _show(self):
        try:
            data = []
            for ff in self.get_foreignfields(True):
                data.append(str(getattr(self, ff)))
            return "{} ({})".format(*data)
        except:
            return str(self.pk) if self.pk else "NOT YET SAVED"
    
    def __str__(self):
        return self._show()
    
    @classmethod
    def get_basefields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields if i != cls._meta.pk and not i.is_relation and not i in cls.exclude]
        
    @classmethod
    def get_foreignfields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields if isinstance(i, models.ForeignKey) and not i in cls.exclude]
        
    @classmethod
    def get_primary_fields(cls, as_string=False):
        return cls.get_basefields(as_string=True)
        
    @classmethod
    def get_m2mfields(cls, as_string=True):
        return [i.name if as_string else i for i in cls._meta.get_fields() if (not isinstance(i, models.ForeignKey) and i.is_relation) and not i in cls.exclude] 
        
    class Meta:
        abstract = True

                                                # GENRES
class m2m_artikel_genre(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'genre')
        db_table = 'DBentry_artikel_genre'
        verbose_name = 'Artikel-Genre'
        verbose_name_plural = 'Artikel-Genres'
    
    
class m2m_band_genre(m2mBase):
    band = models.ForeignKey('band')
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('band', 'genre')
        db_table = 'DBentry_band_genre'
        verbose_name = 'Band-Genre'
        verbose_name_plural = 'Band-Genres'
    
    def __str__(self):
        return "{} ({})".format(str(self.band), str(self.genre))
        
class m2m_magazin_genre(m2mBase):
    magazin = models.ForeignKey('magazin', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('magazin', 'genre')
        db_table = 'DBentry_magazin_genre'
        verbose_name = 'Magazin-Genre'
        verbose_name_plural = 'Magazin-Genres'
    
class m2m_musiker_genre(m2mBase):
    musiker = models.ForeignKey('musiker', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('musiker', 'genre')
        db_table = 'DBentry_musiker_genre'
        verbose_name = 'Musiker-Genre'
        verbose_name_plural = 'Musiker-Genres'
    
class m2m_veranstaltung_genre(m2mBase):
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('veranstaltung', 'genre')
        db_table = 'DBentry_veranstaltung_genre'
        verbose_name = 'Veranstaltung-Genre'
        verbose_name_plural = 'Veranstaltung-Genres'
    
                                                # SCHLAGWÖRTER
                                                
class m2m_artikel_schlagwort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    schlagwort = models.ForeignKey('schlagwort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'schlagwort')
        db_table = 'DBentry_artikel_schlagwort'
        verbose_name = 'Artikel-Schlagwort'
        verbose_name_plural = 'Artikel-Schlagwörter'
    
                                                # ORTE
                                                
class m2m_artikel_ort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    ort = models.ForeignKey('ort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'ort')
        db_table = 'DBentry_artikel_ort'
        verbose_name = 'Artikel-Ort'
        verbose_name_plural = 'Artikel-Orte'
    
                                                # SPIELORTE
                                                
class m2m_artikel_spielort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    spielort = models.ForeignKey('spielort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'spielort')
        db_table = 'DBentry_artikel_spielort'
        verbose_name = 'Artikel-Spielort'
        verbose_name_plural = 'Artikel-Spielorte'
    
                                                # VERANSTALTUNGEN
                                                
class m2m_artikel_veranstaltung(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'veranstaltung')
        db_table = 'DBentry_artikel_veranstaltung'
        verbose_name = 'Artikel-Veranstaltung'
        verbose_name_plural = 'Artikel-Veranstaltungen'
    
                                                # PERSONEN
                                                
class m2m_artikel_person(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    person = models.ForeignKey('person', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'person')
        db_table = 'DBentry_artikel_person'
        verbose_name = 'Artikel-Person'
        verbose_name_plural = 'Artikel-Personen'
                                                
class m2m_veranstaltung_person(m2mBase):
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    person = models.ForeignKey('person', models.PROTECT)
    class Meta:
        unique_together = ('veranstaltung', 'person')
        db_table = 'DBentry_veranstaltung_person'
        verbose_name = 'Veranstaltung-Person'
        verbose_name_plural = 'Veranstaltung-Personen'
    
                                                # AUTOREN
                                                
class m2m_artikel_autor(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    autor = models.ForeignKey('autor', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'autor')
        db_table = 'DBentry_artikel_autor'
        verbose_name = 'Artikel-Autor'
        verbose_name_plural = 'Artikel-Autoren'
    
class m2m_buch_autor(m2mBase):
    buch = models.ForeignKey('buch', models.PROTECT)
    autor = models.ForeignKey('autor', models.PROTECT)
    class Meta:
        unique_together = ('buch', 'autor')
        db_table = 'DBentry_buch_autor'
        verbose_name = 'Buch-Autor'
        verbose_name_plural = 'Buch-Autoren'
    
                                                # MUSIKER
                                                
class m2m_artikel_musiker(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    musiker = models.ForeignKey('musiker', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'musiker')
        db_table = 'DBentry_artikel_musiker'
        verbose_name = 'Artikel-Musiker'
        verbose_name_plural = 'Artikel-Musiker'
                                                
class m2m_band_musiker(m2mBase):
    band = models.ForeignKey('band')
    musiker = models.ForeignKey('musiker', models.PROTECT)
    class Meta:
        unique_together = ('band', 'musiker')
        db_table = 'DBentry_band_musiker'
        verbose_name = 'Band-Mitglied'
        verbose_name_plural = 'Band-Mitglieder'
        
                                                # BANDS
                                                
class m2m_artikel_band(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    band = models.ForeignKey('band')
    class Meta:
        unique_together = ('artikel', 'band')
        db_table = 'DBentry_artikel_band'
        verbose_name = 'Artikel-Band'
        verbose_name_plural = 'Artikel-Bands'
    
class m2m_veranstaltung_band(m2mBase):
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    band = models.ForeignKey('band', models.PROTECT)
    class Meta:
        unique_together = ('veranstaltung', 'band')
        db_table = 'DBentry_veranstaltung_band'
        verbose_name = 'Veranstaltung-Band'
        verbose_name_plural = 'Veranstaltung-Bands'
    
                                                # INSTRUMENTE
                                                
class m2m_musiker_instrument(m2mBase):
    musiker = models.ForeignKey('musiker', models.PROTECT)
    instrument = models.ForeignKey('instrument', models.PROTECT)
    class Meta:
        unique_together = ('musiker', 'instrument')
        db_table = 'DBentry_musiker_instrument'
        verbose_name = 'Musiker-Instrument'
        verbose_name_plural = 'Musiker-Instrumente'
    
                                                # MAGAZINE
                                                
class m2m_autor_magazin(m2mBase):
    autor = models.ForeignKey('autor', models.PROTECT)
    magazin = models.ForeignKey('magazin')
    class Meta:
        unique_together = ('autor', 'magazin')
        db_table = 'DBentry_autor_magazin'
        verbose_name = 'Autor-Magazin'
        verbose_name_plural = 'Autor-Magazine'
    
