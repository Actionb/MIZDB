
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
class m2m_audio_genre(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'genre')
        db_table = 'DBentry_audio_genre'
        verbose_name = 'Audio-Genre'
        verbose_name_plural = 'Audio-Genres'
        
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
        
class m2m_video_genre(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    genre = models.ForeignKey('genre', models.PROTECT)
    class Meta:
        unique_together = ('video', 'genre')
        db_table = 'DBentry_video_genre'
        verbose_name = 'Video-Genre'
        verbose_name_plural = 'Video-Genres'
    
                                                # SCHLAGWÖRTER
class m2m_audio_schlagwort(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    schlagwort = models.ForeignKey('schlagwort', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'schlagwort')
        db_table = 'DBentry_audio_schlagwort'
        verbose_name = 'Audio-Schlagwort'
        verbose_name_plural = 'Audio-Schlagworte'
                                                
class m2m_artikel_schlagwort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    schlagwort = models.ForeignKey('schlagwort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'schlagwort')
        db_table = 'DBentry_artikel_schlagwort'
        verbose_name = 'Artikel-Schlagwort'
        verbose_name_plural = 'Artikel-Schlagwörter'
        
class m2m_video_schlagwort(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    schlagwort = models.ForeignKey('schlagwort', models.PROTECT)
    class Meta:
        unique_together = ('video', 'schlagwort')
        db_table = 'DBentry_video_schlagwort'
        verbose_name = 'Video-Schlagwort'
        verbose_name_plural = 'Video-Schlagwörter'
    
                                                # ORTE
                                                
class m2m_audio_ort(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    ort = models.ForeignKey('ort', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'ort')
        db_table = 'DBentry_audio_ort'
        verbose_name = 'Audio-Ort'
        verbose_name_plural = 'Audio-Orte'
                                                
class m2m_artikel_ort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    ort = models.ForeignKey('ort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'ort')
        db_table = 'DBentry_artikel_ort'
        verbose_name = 'Artikel-Ort'
        verbose_name_plural = 'Artikel-Orte'
    
                                                # SPIELORTE
        
class m2m_audio_spielort(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    spielort = models.ForeignKey('spielort', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'spielort')
        db_table = 'DBentry_audio_spielort'
        verbose_name = 'Audio-Spielort'
        verbose_name_plural = 'Audio-Spielorte'
                                                
class m2m_artikel_spielort(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    spielort = models.ForeignKey('spielort', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'spielort')
        db_table = 'DBentry_artikel_spielort'
        verbose_name = 'Artikel-Spielort'
        verbose_name_plural = 'Artikel-Spielorte'
        
class m2m_video_spielort(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    spielort = models.ForeignKey('spielort', models.PROTECT)
    class Meta:
        unique_together = ('video', 'spielort')
        db_table = 'DBentry_video_spielort'
        verbose_name = 'Video-Spielort'
        verbose_name_plural = 'Video-Spielorte'
    
                                                # VERANSTALTUNGEN
        
class m2m_audio_veranstaltung(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'veranstaltung')
        db_table = 'DBentry_audio_veranstaltung'
        verbose_name = 'Audio-Veranstaltung'
        verbose_name_plural = 'Audio-Veranstaltungen'
                                                
class m2m_artikel_veranstaltung(m2mBase):
    artikel = models.ForeignKey('artikel', models.PROTECT)
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    class Meta:
        unique_together = ('artikel', 'veranstaltung')
        db_table = 'DBentry_artikel_veranstaltung'
        verbose_name = 'Artikel-Veranstaltung'
        verbose_name_plural = 'Artikel-Veranstaltungen'
        
class m2m_video_veranstaltung(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    veranstaltung = models.ForeignKey('veranstaltung', models.PROTECT)
    class Meta:
        unique_together = ('video', 'veranstaltung')
        db_table = 'DBentry_video_veranstaltung'
        verbose_name = 'Video-Veranstaltung'
        verbose_name_plural = 'Video-Veranstaltungen'
    
                                                # PERSONEN
                                                
class m2m_audio_person(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    person = models.ForeignKey('person', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'person')
        db_table = 'DBentry_audio_person'
        verbose_name = 'Audio-Person'
        verbose_name_plural = 'Audio-Personen'
                                                
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
        
class m2m_video_person(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    person = models.ForeignKey('person', models.PROTECT)
    class Meta:
        unique_together = ('video', 'person')
        db_table = 'DBentry_video_person'
        verbose_name = 'Video-Person'
        verbose_name_plural = 'Video-Personen'
    
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
                                                
class m2m_audio_musiker(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    musiker = models.ForeignKey('musiker', models.PROTECT)
    instrument = models.ManyToManyField('instrument', verbose_name = 'Instrumente', blank = True)
    class Meta:
        unique_together = ('audio', 'musiker')
        db_table = 'DBentry_audio_musiker'
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'
                                                
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
                                                
class m2m_video_musiker(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    musiker = models.ForeignKey('musiker', models.PROTECT)
    class Meta:
        unique_together = ('video', 'musiker')
        db_table = 'DBentry_video_musiker'
        verbose_name = 'Video-Musiker'
        verbose_name_plural = 'Video-Musiker'
        
                                                # BANDS
class m2m_audio_band(m2mBase):
    audio = models.ForeignKey('audio', models.PROTECT)
    band = models.ForeignKey('band', models.PROTECT)
    class Meta:
        unique_together = ('audio', 'band')
        db_table = 'DBentry_audio_band'
        verbose_name = 'Audio-Band'
        verbose_name_plural = 'Audio-Bands'
                                                
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
        
class m2m_video_band(m2mBase):
    video = models.ForeignKey('video', models.PROTECT)
    band = models.ForeignKey('band', models.PROTECT)
    class Meta:
        unique_together = ('video', 'band')
        db_table = 'DBentry_video_band'
        verbose_name = 'Video-Band'
        verbose_name_plural = 'Video-Bands'
    
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
    

                                                # DATEI RELATIONEN
    
class m2m_datei_genre(m2mBase):
    datei = models.ForeignKey('datei')
    genre = models.ForeignKey('genre')
    class Meta:
        unique_together = ('datei', 'genre')
        db_table = 'DBentry_datei_genre'
        verbose_name = 'Datei-Genre'
        verbose_name_plural = 'Datei-Genres'  
        
class m2m_datei_schlagwort(m2mBase):
    datei = models.ForeignKey('datei')
    schlagwort = models.ForeignKey('schlagwort')
    class Meta:
        unique_together = ('datei', 'schlagwort')
        db_table = 'DBentry_datei_schlagwort'
        verbose_name = 'Datei-Schlagwort'
        verbose_name_plural = 'Datei-Schlagwörter'
        
class m2m_datei_person(m2mBase):
    datei = models.ForeignKey('datei')
    person = models.ForeignKey('person')
    class Meta:
        unique_together = ('datei', 'person')
        db_table = 'DBentry_datei_person'
        verbose_name = 'Datei-Person'
        verbose_name_plural = 'Datei-Personen'
        
class m2m_datei_band(m2mBase):
    datei = models.ForeignKey('datei')
    band = models.ForeignKey('band')
    class Meta:
        unique_together = ('datei', 'band')
        db_table = 'DBentry_datei_band'
        verbose_name = 'Datei-Band'
        verbose_name_plural = 'Datei-Bands'
        
class m2m_datei_musiker(m2mBase):
    datei = models.ForeignKey('datei')
    musiker = models.ForeignKey('musiker')
    instrument = models.ManyToManyField('instrument', verbose_name = 'Instrumente', blank = True)
    class Meta:
        unique_together = ('datei', 'musiker')
        db_table = 'DBentry_datei_musiker'
        verbose_name = 'Datei-Musiker'
        verbose_name_plural = 'Datei-Musiker'
        
    def __str__(self):
        if self.instrument.exists():
            instr = ",".join([str(i.kuerzel) for i in self.instrument.all()])
            return "{} ({})".format(str(getattr(self, 'musiker')), instr)
        return str(getattr(self, 'musiker'))
        
class m2m_datei_ort(m2mBase):
    datei = models.ForeignKey('datei')
    ort = models.ForeignKey('ort')
    class Meta:
        unique_together = ('datei', 'ort')
        db_table = 'DBentry_datei_ort'
        verbose_name = 'Datei-Ort'
        verbose_name_plural = 'Datei-Orte'
        
class m2m_datei_spielort(m2mBase):
    datei = models.ForeignKey('datei')
    spielort = models.ForeignKey('spielort')
    class Meta:
        unique_together = ('datei', 'spielort')
        db_table = 'DBentry_datei_spielort'
        verbose_name = 'Datei-Spielort'
        verbose_name_plural = 'Datei-Spielorte'
        
class m2m_datei_veranstaltung(m2mBase):
    datei = models.ForeignKey('datei')
    veranstaltung = models.ForeignKey('veranstaltung')
    class Meta:
        unique_together = ('datei', 'veranstaltung')
        db_table = 'DBentry_datei_veranstaltung'
        verbose_name = 'Datei-Veranstaltung'
        verbose_name_plural = 'Datei-Veranstaltungen'
        
class m2m_datei_quelle(m2mBase):
    datei = models.ForeignKey('datei')
    audio = models.ForeignKey('audio', on_delete = models.SET_NULL, blank = True, null = True)
    bildmaterial = models.ForeignKey('bildmaterial', on_delete = models.SET_NULL, blank = True, null = True)
    buch = models.ForeignKey('buch', on_delete = models.SET_NULL, blank = True, null = True)
    dokument = models.ForeignKey('dokument', on_delete = models.SET_NULL, blank = True, null = True)
    memorabilien = models.ForeignKey('memorabilien', on_delete = models.SET_NULL, blank = True, null = True)
    video = models.ForeignKey('video', on_delete = models.SET_NULL, blank = True, null = True)
    class Meta:
        db_table = 'DBentry_datei_quelle'
        verbose_name = 'Datei-Quelle'
        verbose_name_plural = 'Datei-Quellen'
        
    def get_quelle_art(self, as_field = True):
        for fld in m2m_datei_quelle.get_foreignfields():
            if fld.name != 'datei' and fld.value_from_object(self):
                if as_field:
                    return fld
                else:
                    return fld.name
        return ''
        
    def __str__(self):
        art = self.get_quelle_art()
        if art:
            return '{} ({})'.format(str(getattr(self, art.name)), art.related_model._meta.verbose_name)
        else:
            return super(m2m_datei_quelle, self).__str__()

class m2m_audio_plattenfirma(m2mBase):
    audio = models.ForeignKey('audio')
    plattenfirma = models.ForeignKey('plattenfirma')
    class Meta:
        db_table = 'DBentry_audio_plattenfirma'
        verbose_name = 'Audio-Plattenfirma'
        verbose_name_plural = 'Audio-Plattenfirmen'
