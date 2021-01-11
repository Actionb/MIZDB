from django.db import models
from DBentry.base.models import BaseM2MModel
from DBentry.utils.models import get_model_fields


class m2m_audio_musiker(BaseM2MModel):
    audio = models.ForeignKey('Audio', models.CASCADE)
    musiker = models.ForeignKey('Musiker', models.CASCADE)
    instrument = models.ManyToManyField(
        'instrument', verbose_name='Instrumente', blank=True
    )

    name_field = 'musiker'

    class Meta:
        unique_together = ('audio', 'musiker')
        db_table = 'DBentry_audio_musiker'
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'


class m2m_video_musiker(BaseM2MModel):
    video = models.ForeignKey('Video', models.CASCADE)
    musiker = models.ForeignKey('Musiker', models.CASCADE)
    instrument = models.ManyToManyField(
        'instrument', verbose_name='Instrumente', blank=True
    )

    name_field = 'musiker'

    class Meta:
        unique_together = ('video', 'musiker')
        db_table = 'DBentry_video_musiker'
        verbose_name = 'Video-Musiker'
        verbose_name_plural = 'Video-Musiker'


class m2m_datei_musiker(BaseM2MModel):
    datei = models.ForeignKey('Datei', models.CASCADE)
    musiker = models.ForeignKey('Musiker', models.CASCADE)
    instrument = models.ManyToManyField(
        'instrument', verbose_name='Instrumente', blank=True
    )
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
    # TODO: rework this, you should only ever be able to select one relation to
    # a non-datei object (OneToOne?)
    datei = models.ForeignKey('Datei', models.CASCADE)
    audio = models.ForeignKey('Audio', models.SET_NULL, blank=True, null=True)
    bildmaterial = models.ForeignKey('Bildmaterial', models.SET_NULL, blank=True, null=True)
    buch = models.ForeignKey('Buch', models.SET_NULL, blank=True, null=True)
    dokument = models.ForeignKey('Dokument', models.SET_NULL, blank=True, null=True)
    memorabilien = models.ForeignKey('Memorabilien', models.SET_NULL, blank=True, null=True)
    video = models.ForeignKey('Video', models.SET_NULL, blank=True, null=True)
    class Meta:
        db_table = 'DBentry_datei_quelle'
        verbose_name = 'Datei-Quelle'
        verbose_name_plural = 'Datei-Quellen'

    def get_quelle_art(self, as_field=True):
        return None
        foreignkey_fields = get_model_fields(
            m2m_datei_quelle, base=False, foreign=True, m2m=False)
        for fld in foreignkey_fields:
            if fld.name != 'datei' and fld.value_from_object(self):
                if as_field:
                    return fld
                else:
                    return fld.name
        return ''

    def __str__(self):
        art = self.get_quelle_art()
        if art:
            return '{} ({})'.format(
                str(getattr(self, art.name)), art.related_model._meta.verbose_name
            )
        else:
            return super(m2m_datei_quelle, self).__str__()

    @classmethod
    def _check_has_m2m_field(cls, **kwargs):
        # This is one whacky model, ignore that check for now...
        return []
