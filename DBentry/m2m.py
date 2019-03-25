
from django.db import models
from DBentry.base.models import BaseM2MModel

# ================================= #
##              AUDIO
# ================================= #

class m2m_audio_ausgabe(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'ausgabe')
        db_table = 'DBentry_audio_ausgabe'
        verbose_name = 'Musik-Beilage'
        verbose_name_plural = 'Musik-Beilagen'
        
class m2m_audio_band(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    band = models.ForeignKey('band', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'band')
        db_table = 'DBentry_audio_band'
        verbose_name = 'Audio-Band'
        verbose_name_plural = 'Audio-Bands'
        
class m2m_audio_genre(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    genre = models.ForeignKey('genre', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'genre')
        db_table = 'DBentry_audio_genre'
        verbose_name = 'Audio-Genre'
        verbose_name_plural = 'Audio-Genres'
        
class m2m_audio_musiker(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    musiker = models.ForeignKey('musiker', models.CASCADE)
    instrument = models.ManyToManyField('instrument', verbose_name = 'Instrumente', blank = True)
    class Meta:
        unique_together = ('audio', 'musiker')
        db_table = 'DBentry_audio_musiker'
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'
                                                
class m2m_audio_ort(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    ort = models.ForeignKey('ort', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'ort')
        db_table = 'DBentry_audio_ort'
        verbose_name = 'Audio-Ort'
        verbose_name_plural = 'Audio-Orte'
        
class m2m_audio_person(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    person = models.ForeignKey('person', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'person')
        db_table = 'DBentry_audio_person'
        verbose_name = 'Audio-Person'
        verbose_name_plural = 'Audio-Personen'

class m2m_audio_plattenfirma(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    plattenfirma = models.ForeignKey('plattenfirma', models.CASCADE)
    class Meta:
        db_table = 'DBentry_audio_plattenfirma'
        verbose_name = 'Audio-Plattenfirma'
        verbose_name_plural = 'Audio-Plattenfirmen'
        
class m2m_audio_schlagwort(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    schlagwort = models.ForeignKey('schlagwort', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'schlagwort')
        db_table = 'DBentry_audio_schlagwort'
        verbose_name = 'Audio-Schlagwort'
        verbose_name_plural = 'Audio-Schlagworte'
                                                
class m2m_audio_spielort(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    spielort = models.ForeignKey('spielort', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'spielort')
        db_table = 'DBentry_audio_spielort'
        verbose_name = 'Audio-Spielort'
        verbose_name_plural = 'Audio-Spielorte'
        
class m2m_audio_veranstaltung(BaseM2MModel):
    audio = models.ForeignKey('audio', models.CASCADE)
    veranstaltung = models.ForeignKey('veranstaltung', models.CASCADE)
    class Meta:
        unique_together = ('audio', 'veranstaltung')
        db_table = 'DBentry_audio_veranstaltung'
        verbose_name = 'Audio-Veranstaltung'
        verbose_name_plural = 'Audio-Veranstaltungen'
                                                

# ================================= #
##              ARTIKEL
# ================================= #
                                                
class m2m_artikel_autor(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    autor = models.ForeignKey('autor', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'autor')
        db_table = 'DBentry_artikel_autor'
        verbose_name = 'Artikel-Autor'
        verbose_name_plural = 'Artikel-Autoren'
                                                
class m2m_artikel_band(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    band = models.ForeignKey('band', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'band')
        db_table = 'DBentry_artikel_band'
        verbose_name = 'Artikel-Band'
        verbose_name_plural = 'Artikel-Bands'
        
class m2m_artikel_genre(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    genre = models.ForeignKey('genre', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'genre')
        db_table = 'DBentry_artikel_genre'
        verbose_name = 'Artikel-Genre'
        verbose_name_plural = 'Artikel-Genres'
                                                
class m2m_artikel_musiker(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    musiker = models.ForeignKey('musiker', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'musiker')
        db_table = 'DBentry_artikel_musiker'
        verbose_name = 'Artikel-Musiker'
        verbose_name_plural = 'Artikel-Musiker'
                                                
class m2m_artikel_ort(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    ort = models.ForeignKey('ort', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'ort')
        db_table = 'DBentry_artikel_ort'
        verbose_name = 'Artikel-Ort'
        verbose_name_plural = 'Artikel-Orte'
                                                
class m2m_artikel_person(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    person = models.ForeignKey('person', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'person')
        db_table = 'DBentry_artikel_person'
        verbose_name = 'Artikel-Person'
        verbose_name_plural = 'Artikel-Personen'
                                                
class m2m_artikel_schlagwort(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    schlagwort = models.ForeignKey('schlagwort', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'schlagwort')
        db_table = 'DBentry_artikel_schlagwort'
        verbose_name = 'Artikel-Schlagwort'
        verbose_name_plural = 'Artikel-Schlagwörter'
        
class m2m_artikel_spielort(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    spielort = models.ForeignKey('spielort', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'spielort')
        db_table = 'DBentry_artikel_spielort'
        verbose_name = 'Artikel-Spielort'
        verbose_name_plural = 'Artikel-Spielorte'
                                                
class m2m_artikel_veranstaltung(BaseM2MModel):
    artikel = models.ForeignKey('artikel', models.CASCADE)
    veranstaltung = models.ForeignKey('veranstaltung', models.CASCADE)
    class Meta:
        unique_together = ('artikel', 'veranstaltung')
        db_table = 'DBentry_artikel_veranstaltung'
        verbose_name = 'Artikel-Veranstaltung'
        verbose_name_plural = 'Artikel-Veranstaltungen'
        
        
# ================================= #
##              BANDS
# ================================= #
    
class m2m_band_genre(BaseM2MModel):
    band = models.ForeignKey('band', models.CASCADE)
    genre = models.ForeignKey('genre', models.CASCADE)
    class Meta:
        unique_together = ('band', 'genre')
        db_table = 'DBentry_band_genre'
        verbose_name = 'Band-Genre'
        verbose_name_plural = 'Band-Genres'
        
    def __str__(self):
        return "{} ({})".format(str(self.band), str(self.genre))
        
class m2m_band_musiker(BaseM2MModel):
    band = models.ForeignKey('band', models.CASCADE)
    musiker = models.ForeignKey('musiker', models.CASCADE)
    class Meta:
        unique_together = ('band', 'musiker')
        db_table = 'DBentry_band_musiker'
        verbose_name = 'Band-Mitglied'
        verbose_name_plural = 'Band-Mitglieder'

# ================================= #
##              MAGAZIN
# ================================= #
                                                
class m2m_autor_magazin(BaseM2MModel):
    autor = models.ForeignKey('autor', models.CASCADE)
    magazin = models.ForeignKey('magazin', models.CASCADE)
    class Meta:
        unique_together = ('autor', 'magazin')
        db_table = 'DBentry_autor_magazin'
        verbose_name = 'Autor-Magazin'
        verbose_name_plural = 'Autor-Magazine'
        
class m2m_magazin_genre(BaseM2MModel):
    magazin = models.ForeignKey('magazin', models.CASCADE)
    genre = models.ForeignKey('genre', models.CASCADE)
    class Meta:
        unique_together = ('magazin', 'genre')
        db_table = 'DBentry_magazin_genre'
        verbose_name = 'Magazin-Genre'
        verbose_name_plural = 'Magazin-Genres'
        
class m2m_magazin_verlag(BaseM2MModel):
    magazin = models.ForeignKey('magazin', models.CASCADE)
    verlag = models.ForeignKey('verlag', models.CASCADE)
    start = models.CharField('von', max_length = 123, blank = True)
    end = models.CharField('bis', max_length = 123, blank = True)
    class Meta:
        unique_together = ('magazin', 'verlag')
        verbose_name = 'Magazin-Verlag'
        verbose_name_plural = 'Magazin-Verlage'
        
    def __str__(self):
        return str(self.verlag)
    
class m2m_magazin_herausgeber(BaseM2MModel):
    magazin = models.ForeignKey('magazin', models.CASCADE)
    herausgeber = models.ForeignKey('Herausgeber', models.CASCADE)
    start = models.CharField('von', max_length = 123, blank = True)
    end = models.CharField('bis', max_length = 123, blank = True)
    class Meta:
        unique_together = ('magazin', 'herausgeber')
        verbose_name = 'Magazin-Herausgeber'
        verbose_name_plural = 'Magazin-Herausgeber'
        
    def __str__(self):
        return str(self.herausgeber)
    

# ================================= #
##              MUSIKER
# ================================= #
                                               
class m2m_musiker_genre(BaseM2MModel):
    musiker = models.ForeignKey('musiker', models.CASCADE)
    genre = models.ForeignKey('genre', models.CASCADE)
    class Meta:
        unique_together = ('musiker', 'genre')
        db_table = 'DBentry_musiker_genre'
        verbose_name = 'Musiker-Genre'
        verbose_name_plural = 'Musiker-Genres'
                                                
class m2m_musiker_instrument(BaseM2MModel):
    musiker = models.ForeignKey('musiker', models.CASCADE)
    instrument = models.ForeignKey('instrument', models.CASCADE)
    class Meta:
        unique_together = ('musiker', 'instrument')
        db_table = 'DBentry_musiker_instrument'
        verbose_name = 'Musiker-Instrument'
        verbose_name_plural = 'Musiker-Instrumente'
        
# ================================= #
##              VIDEO
# ================================= #
                                     
class m2m_video_musiker(BaseM2MModel):
    video = models.ForeignKey('video', models.CASCADE)
    musiker = models.ForeignKey('musiker', models.CASCADE)
    instrument = models.ManyToManyField('instrument', verbose_name = 'Instrumente', blank = True)
    class Meta:
        unique_together = ('video', 'musiker')
        db_table = 'DBentry_video_musiker'
        verbose_name = 'Video-Musiker'
        verbose_name_plural = 'Video-Musiker'
    

# ================================= #
##              DATEI
# ================================= #
        
class m2m_datei_musiker(BaseM2MModel):
    datei = models.ForeignKey('datei', models.CASCADE)
    musiker = models.ForeignKey('musiker', models.CASCADE)
    instrument = models.ManyToManyField('instrument', verbose_name = 'Instrumente', blank = True)
    class Meta:
        unique_together = ('datei', 'musiker')
        db_table = 'DBentry_datei_musiker'
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        
    def __str__(self):
        if self.instrument.exists():
            instr = ",".join([str(i.kuerzel) for i in self.instrument.all()])
            return "{} ({})".format(str(getattr(self, 'musiker')), instr)
        return str(getattr(self, 'musiker'))
        
class m2m_datei_quelle(BaseM2MModel):
    #TODO: rework this, you should only ever be able to select one relation to a non-datei object (OneToOne?)
    datei = models.ForeignKey('datei', models.CASCADE)
    audio = models.ForeignKey('audio', models.SET_NULL, blank = True, null = True)
    bildmaterial = models.ForeignKey('bildmaterial', models.SET_NULL, blank = True, null = True)
    buch = models.ForeignKey('buch', models.SET_NULL, blank = True, null = True)
    dokument = models.ForeignKey('dokument', models.SET_NULL, blank = True, null = True)
    memorabilien = models.ForeignKey('memorabilien', models.SET_NULL, blank = True, null = True)
    video = models.ForeignKey('video', models.SET_NULL, blank = True, null = True)
    class Meta:
        db_table = 'DBentry_datei_quelle'
        verbose_name = 'Datei-Quelle'
        verbose_name_plural = 'Datei-Quellen'
        
    def get_quelle_art(self, as_field = True):
        return None
        #TODO: get_foreignfields no longer exists!
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
