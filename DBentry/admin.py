from django.contrib import admin, messages

from django.utils.html import format_html
from django.contrib.admin.utils import get_fields_from_path

from .models import *
from .helper import *
from .constants import *
from .forms import *
from .utils import link_list

from .changelist import MIZChangeList

from django.contrib.admin.options import *
class ModelBase(admin.ModelAdmin):
    
    def __init__(self, *args, **kwargs):
        super(ModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(self.model)
        if not self.search_fields:
            self.search_fields = list(self.model.get_search_fields())
        
    search_fields_redirect = dict()
    flds_to_group = []
    crosslinks = []
    gogglebtns = []
    
    def has_adv_sf(self):
        return len(getattr(self, 'advanced_search_form', []))>0
    
    def get_changelist(self, request, **kwargs):
        return MIZChangeList
    
    def get_exclude(self, request, obj = None):
        self.exclude = super(ModelBase, self).get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if hasattr(fld, 'm2m_field_name'):
                    self.exclude.append(fld.name)
        return self.exclude
    
    def get_fields(self, request, obj = None):
        if not self.fields:
            self.fields = super(ModelBase, self).get_fields(request, obj)
            if self.flds_to_group:
                self.fields = self.group_fields()
        return self.fields
    
    def group_fields(self):
        if self.fields is None:
            return None
        fields = self.fields
        for tpl in self.flds_to_group:
            try:
                if tpl[0] in fields:
                    if len(tpl)==3 and tpl[-1] == 1:
                        # tuple has a third part which tells us which of the fields to group takes priority
                        fields[ fields.index(tpl[0])] = (tpl[1], tpl[0])
                    else:
                        fields[ fields.index(tpl[0])] = (tpl[0], tpl[1])
                if tpl[1] in fields:
                        fields.remove(tpl[1])
            except:
                pass
        return fields
    
    def get_search_fields(self, request=None):
        if self.search_fields:
            return self.search_fields
        return list(self.model.get_search_fields())
        
    def add_crosslinks(self, object_id):
        from django.contrib.admin.utils import reverse
        from django.db.models.fields.reverse_related import ManyToOneRel
        from django.db.models.fields.related import ManyToManyField
        new_extra = {}
        new_extra['crosslinks'] = []
        
        inlmdls = {i.model for i in self.inlines}
        # Build relations
        for relation_name in getattr(self, 'crosslinks', []):
            path = get_fields_from_path(self.model, relation_name)
            #NOTE: path[0] or path[-1]?
            model = path[0].related_model
            fld_name = path[0].remote_field.name
            if model in inlmdls:
                continue
            try:
                link = reverse("admin:{}_{}_changelist".format(self.opts.app_label, model._meta.model_name)) \
                                + "?" + fld_name + "=" + object_id
            except Exception as e:
                continue
            count = model._default_manager.filter(**{fld_name:object_id}).count()
            
            label = model._meta.verbose_name_plural + "({})".format(count)
            new_extra['crosslinks'].append( dict(link=link, label=label) )
        
        return new_extra
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = extra_context or {}
        new_extra.update(self.add_crosslinks(object_id))
        return super(ModelBase, self).change_view(request, object_id, form_url, new_extra   )
        
    def lookup_allowed(self, key, value):
        if self.has_adv_sf():
            # allow lookups defined in advanced_search_form
            for list in getattr(self, 'advanced_search_form').values():
                if key in list:
                    return True
        if key in [i[0] if isinstance(i, tuple) else i for i in self.list_filter]:
            # allow lookups defined in list_filter
            return True
        return super(ModelBase, self).lookup_allowed(key, value)
        
    def get_changeform_initial_data(self, request):
        """ Turn _changelist_filters string into a useable dict of field_path:value
            so we can fill some formfields with initial values later on. 
            IMPORTANT: THIS ONLY GOVERNS FORMFIELDS FOR ADD-VIEWS. """
        from django.utils.http import unquote
        initial = super(ModelBase, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys() or not initial['_changelist_filters']:
            return initial
            
        # At this point, _changelist_filters is a string of format:
        # '_changelist_filters': 'ausgabe__magazin=47&ausgabe=4288'
        filter_dict = {}
        for part in initial['_changelist_filters'].split('&'):
            if part and SEARCH_TERM_SEP in part:
                if part.startswith("q="):
                    # This part is a string typed into the searchbar, ignore it
                    continue
                try:
                    k, v = part.split(SEARCH_TERM_SEP)
                except ValueError:
                    continue
                if k not in initial.keys():
                    filter_dict[k] = v
        initial.update(filter_dict)
        return initial

    def merge_records(self, request, queryset):
        if queryset.count() == 1:
            self.message_user(request,'Bitte mindestens zwei Datensätze auswählen.', 'warning')
            return
        original_pk = queryset.first().pk
        queryset = queryset.exclude(pk=original_pk)
        duplicates = [i.pk for i in queryset]
        queryset.model.merge(original_pk, duplicates, verbose = False)
    merge_records.short_description = 'Datensätze zusammenfügen'
    

class TabModelBase(admin.TabularInline):
    original = False
    verbose_model = None
    extra = 1
    def __init__(self, *args, **kwargs):
        super(TabModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural

class AliasTabBase(TabModelBase):
    verbose_name_plural = 'Alias'
    
class BestandModelBase(TabModelBase):
    model = bestand
    readonly_fields = ['signatur']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = bestand._meta.verbose_name
    verbose_name_plural = bestand._meta.verbose_name_plural
    
class GenreModelBase(TabModelBase):
    verbose_name = genre._meta.verbose_name
    verbose_name_plural = genre._meta.verbose_name_plural
    
class SchlagwortModelBase(TabModelBase):
    verbose_name = schlagwort._meta.verbose_name
    verbose_name_plural = schlagwort._meta.verbose_name_plural
    
    
@admin.register(audio)
class AudioAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = audio.genre.through
        extra = 1
    class SchlInLine(SchlagwortModelBase):
        model = audio.schlagwort.through
        extra = 1
    class PersonInLine(TabModelBase):
        model = audio.person.through
        verbose_model = person
    class MusikerInLine(TabModelBase):
        model = audio.musiker.through
        verbose_model = musiker
    class BandInLine(TabModelBase):
        model = audio.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = audio.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = audio.veranstaltung.through
        verbose_model = veranstaltung
    class BestandInLine(BestandModelBase):
        pass
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]

class BestandListFilter(admin.SimpleListFilter):
    title = "Bestand vorhanden"
    parameter_name = "bestand"
    
    def lookups(self, request, model_admin):
        lks = [('zraum','Zeitschriftenraum'),('nzraum','nicht im Zeitschriftenraum'),
                ('dubl', 'als Dublette'), ('ndubl', 'nicht als Dublette')]
        return lks
    
    def queryset(self, request, queryset):
        if self.value()=='zraum':
            return queryset.filter(bestand__lagerort_id=ZRAUM_ID)
        if self.value()=='dubl':
            return queryset.filter(bestand__lagerort_id=DUPLETTEN_ID)
        if self.value()=='nzraum':
            return queryset.exclude(bestand__lagerort_id=ZRAUM_ID)
        if self.value()=='ndubl':
            return queryset.exclude(bestand__lagerort_id=DUPLETTEN_ID)

@admin.register(ausgabe)
class AusgabenAdmin(ModelBase):
    class NumInLine(TabModelBase):
        model = ausgabe_num
        extra = 0
    class MonatInLine(TabModelBase):
        model = ausgabe_monat
        extra = 0
    class LNumInLine(TabModelBase):
        model = ausgabe_lnum
        extra = 0
    class JahrInLine(TabModelBase):
        model = ausgabe_jahr
        extra = 0
        verbose_name_plural = 'erschienen im Jahr'
    class BestandInLine(BestandModelBase):
        pass
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine,  ]
    flds_to_group = [('status', 'sonderausgabe')]
    
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahre', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
    search_fields = ['magazin__magazin_name', 'status', 'e_datum', 
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr','ausgabe_monat__monat__monat']
    search_fields_redirect = { 
                            'bearbeitungsstatus' : 'status',
                            'nr' : 'ausgabe_num__num', 
                            'nummer' : 'ausgabe_num__num', 
                            'lfd' : 'ausgabe_lnum__lnum', 
                            }
                        
    actions = ['add_duplicate', 'add_bestand', 'merge_records', 'num_to_lnum', 'add_birgit', 'bulk_jg']
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum'], 
        'selects':['magazin','status'], 
        'simple':['jahrgang', 'sonderausgabe']
    }
    crosslinks = ['artikel']
       
    # ACTIONS
    def add_duplicate(self, request, queryset):
        try:
            dupletten_lagerort = lagerort.objects.get(pk = DUPLETTEN_ID)
        except:
            self.message_user(request, "Konnte keine Dubletten hinzufügen. Lagerort nicht gefunden.", 'error')
            return
        dupe_list = [bestand(ausgabe=i, lagerort=dupletten_lagerort) for i in queryset]
        try:
            bestand.objects.bulk_create(dupe_list)
        except:
            self.message_user(request, "Konnte keine Dubletten hinzufügen: Interner Fehler.", 'warning')
        else:
            obj_links = link_list(request, [d.ausgabe for d in dupe_list])
            msg_text = "Dublette(n) zu diesen {} Ausgaben hinzugefügt: {}".format(len(dupe_list), obj_links)
            self.message_user(request, format_html(msg_text))
    add_duplicate.short_description = 'Dubletten-Bestand hinzufügen'
    
    def add_bestand(self, request, queryset):
        try:
            zraum_lagerort = lagerort.objects.get(pk = ZRAUM_ID)
        except:
            self.message_user(request, "Konnte keinen Zeitschriftenraum-Bestand hinzufügen. Lagerort nicht gefunden.", 'error')
            return
        zraum_list = []
        dupe_list = []
        for instance in queryset:
            if not bestand.objects.filter(ausgabe=instance, lagerort=zraum_lagerort).exists():
                zraum_list.append(bestand(ausgabe=instance, lagerort=zraum_lagerort))
            else:
                try:
                    dupletten_lagerort = lagerort.objects.get(pk = DUPLETTEN_ID)
                except:
                    continue
                else:
                    dupe_list.append(bestand(ausgabe=instance, lagerort=dupletten_lagerort))
        
        if len(zraum_list):
            try: 
                bestand.objects.bulk_create(zraum_list)
            except:
                self.message_user(request, "Konnte keinen Bestand hinzufügen: Interner Fehler.", 'warning')
                return
        obj_links = link_list(request, [z.ausgabe for z in zraum_list])
        msg_text = "Zeitschriftenraum-Bestand zu diesen {} Ausgaben hinzugefügt: {}".format(len(zraum_list), obj_links)
        self.message_user(request, format_html(msg_text))
        if dupe_list:
            obj_links = link_list(request, [d.ausgabe for d in dupe_list])
            msg_text = 'Folgende {} Ausgaben hatten bereits einen Bestand im Zeitschriftenraum: {}'.format(
                        len(dupe_list), obj_links
                        )
            self.message_user(request, format_html(msg_text), 'warning')
            if AUTO_ASSIGN_DUPLICATE:
                try:
                    bestand.objects.bulk_create(dupe_list)
                except:
                    self.message_user(request, "Konnte keine Dubletten hinzufügen: Interner Fehler.", 'warning')
                else:
                    msg_text = "{} Dubletten hinzugefügt: {}".format(len(dupe_list), obj_links)
                    self.message_user(request, format_html(msg_text))
    add_bestand.short_description = 'Zeitschriftenraum-Bestand hinzufügen'
        
    def num_to_lnum(self, request, queryset):
        to_create = []
        for instance in queryset:
            for num in instance.ausgabe_num_set.values_list('num', flat = True):
                to_create.append(ausgabe_lnum(ausgabe=instance, lnum=num)) #**{'ausgabe':instance, 'lnum':num}
            instance.ausgabe_num_set.all().delete()
            instance.ausgabe_lnum_set.all().delete()
        ausgabe_lnum.objects.bulk_create(to_create)
        
    def add_birgit(self, request, queryset):
        birgit = provenienz.objects.get(pk=6)
        for instance in queryset:
            instance.bestand_set.update(provenienz=birgit)
            
    def bulk_jg(self, request, queryset):
        mag_id = queryset.values_list('magazin_id',  flat = True)
        if mag_id.count() != 1:
            msg_text = "Aktion abgebrochen: Ausgaben-Liste enthält mehr als ein Magazin."
            self.message_user(request, msg_text, 'error')
            return
        jg = 1
        if queryset.first().jahrgang:
            jg = queryset.first().jahrgang
        mag = magazin.objects.get(pk=mag_id)
        mag.ausgabe_set.bulk_add_jg(jg)
    
@admin.register(autor)
class AutorAdmin(ModelBase):
    class MagazinInLine(TabModelBase):
        model = autor.magazin.through
        extra = 1
    
    inlines = [MagazinInLine]
    
    list_display = ['__str__', 'magazin_string']
    search_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    search_fields_redirect = {'vorname':'person__vorname', 'nachname':'person__nachname'}

    crosslinks = ['artikel', 'buch']
    
@admin.register(artikel)
class ArtikelAdmin(ModelBase):  
    class GenreInLine(GenreModelBase):
        model = artikel.genre.through
        extra = 1
    class SchlInLine(SchlagwortModelBase):
        model = artikel.schlagwort.through
        extra = 1
    class PersonInLine(TabModelBase):
        model = artikel.person.through
        verbose_model = person
    class AutorInLine(TabModelBase):
        model = artikel.autor.through
        verbose_model = autor
    class MusikerInLine(TabModelBase):
        model = artikel.musiker.through
        verbose_model = musiker
    class BandInLine(TabModelBase):
        model = artikel.band.through
        verbose_model = band
    class OrtInLine(TabModelBase):
        model = artikel.ort.through
        verbose_model = ort
    class SpielortInLine(TabModelBase):
        model = artikel.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = artikel.veranstaltung.through
        verbose_model = veranstaltung
    inlines = [AutorInLine, SchlInLine, MusikerInLine, BandInLine, GenreInLine, OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine]
    flds_to_group = [('ausgabe','magazin', 1),('seite', 'seitenumfang'),]
    
    list_display = ['__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string','ausgabe','artikel_magazin', 'kuenstler_string']
    list_display_links = ['__str__', 'seite']
    search_fields_redirect = { 
                                'magazin' : 'ausgabe__magazin__magazin_name',
                                'genre' : ['genre', 'musiker__genre', 'band__genre']
                                }
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', 'ausgabe', 'schlagwort', 'genre', 'band', 'musiker', 'autor'], 
        'simple':[], 
    }  
    save_on_top = True

    def get_queryset(self, request):
        from django.db.models import Min
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite', 'pk')
        return qs
        
@admin.register(band)    
class BandAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = band.genre.through
    class MusikerInLine(TabModelBase):
        model = band.musiker.through
        #verbose_model = musiker
    class AliasInLine(AliasTabBase):
        model = band_alias
    save_on_top = True
    inlines=[GenreInLine, AliasInLine, MusikerInLine]
    exclude = ['genre', 'musiker']
    
    list_display = ['band_name', 'genre_string','herkunft', 'musiker_string']

    crosslinks = ['artikel', 'veranstaltung']
    googlebtns = ['band_name']
    
    advanced_search_form = {
        'selects' : ['musiker', 'genre', 'herkunft__land', 'herkunft'], 
        'labels' : {'musiker':'Mitglied','herkunft__land':'Herkunftsland', 'herkunft':'Herkunftsort'}
    }
    
@admin.register(bildmaterial)
class BildmaterialAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    pass
    
@admin.register(buch)
class BuchAdmin(ModelBase):
    class AutorInLine(TabModelBase):
        model = buch.autor.through
        verbose_model = autor
    class BestandInLine(BestandModelBase):
        pass
    save_on_top = True
    inlines = [AutorInLine, BestandInLine]
    flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
    exclude = ['autor']
    
@admin.register(dokument)
class DokumentAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]
    
@admin.register(genre)
class GenreAdmin(ModelBase):
    class AliasInLine(AliasTabBase):
        model = genre_alias
    inlines = [AliasInLine]
    search_fields = ['genre', 'ober_id__genre', 'genre_alias__alias']
    list_display = ['genre', 'alias_string']
    crosslinks = ['artikel', 'band', 'magazin', 'musiker', 'veranstaltung']
    

@admin.register(magazin)
class MagazinAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = magazin.genre.through
        magazin.genre.through.verbose_name = ''
    inlines = [GenreInLine]
    exclude = ['genre']
    
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    crosslinks = ['ausgabe']
    
    advanced_search_form = {
        'selects' : ['ort__land'], 
        'labels' : {'ort__land':'Herausgabeland'}
    }
    

@admin.register(memorabilien)
class MemoAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]

@admin.register(musiker)
class MusikerAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = musiker.genre.through
    class BandInLine(TabModelBase):
        model = band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
    class AliasInLine(AliasTabBase):
        model = musiker_alias
    class InstrInLine(TabModelBase):
        model = musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    save_on_top = True
    inlines = [AliasInLine, GenreInLine, BandInLine, InstrInLine]
    readonly_fields = ['herkunft_string']
    fields = ['kuenstler_name', ('person', 'herkunft_string'), 'beschreibung']
    exclude = ('ist_mitglied', 'instrument', 'genre')
    
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'herkunft_string']
    search_fields = ['kuenstler_name', 'genre__genre', 'band__band_name']
    
    crosslinks = ['artikel']
    googlebtns = ['kuenstler_name']
    
    advanced_search_form = {
        'selects' : ['person', 'genre', 'band', 
                'instrument','person__herkunft__land', 'person__herkunft'], 
        'labels' : {'person__herkunft__land':'Herkunftsland'}
    }
    
@admin.register(person)
class PersonAdmin(ModelBase):
    def Ist_Musiker(self, obj):
        return obj.musiker_set.exists()
    Ist_Musiker.boolean = True
    
    def Ist_Autor(self, obj):
        return obj.autor_set.exists()
    Ist_Autor.boolean = True
    
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    fields = ['vorname', 'nachname', 'herkunft', 'beschreibung']
    crosslinks = ['artikel', 'autor', 'musiker']
    
@admin.register(schlagwort)
class SchlagwortTab(ModelBase):
    class AliasInLine(AliasTabBase):
        model = schlagwort_alias
        extra = 1
    inlines = [AliasInLine]
    search_fields = ['schlagwort', 'ober_id__schlagwort', 'schlagwort_alias__alias']
    crosslinks = ['artikel']
    
@admin.register(spielort)
class SpielortAdmin(ModelBase):
    pass
    
@admin.register(technik)
class TechnikAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]

@admin.register(veranstaltung)
class VeranstaltungAdmin(ModelBase):
    pass
#    class GenreInLine(GenreModelBase):
#        model = veranstaltung.genre.through
#    class BandInLine(TabModelBase):
#        model = veranstaltung.band.through
#        verbose_model = band
#    class PersonInLine(TabModelBase):
#        model = veranstaltung.person.through
#        verbose_model = person
#    inlines=[GenreInLine, BandInLine, PersonInLine]
#    exclude = ['genre', 'band', 'person']
    
@admin.register(verlag)
class VerlagAdmin(ModelBase):
    list_display = ['verlag_name', 'sitz']
    search_fields = ['verlag_name', 'sitz__land__land_name', 'sitz__stadt']
    advanced_search_form = {
        'selects' : ['sitz'], 
        'labels' : {'sitz':'Sitz'}
    }
    crosslinks = ['magazin']
    
        
@admin.register(video)
class VideoAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = video.genre.through
        extra = 1
    class SchlInLine(SchlagwortModelBase):
        model = video.schlagwort.through
        extra = 1
    class PersonInLine(TabModelBase):
        model = video.person.through
        verbose_model = person
    class MusikerInLine(TabModelBase):
        model = video.musiker.through
        verbose_model = musiker
    class BandInLine(TabModelBase):
        model = video.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = video.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = video.veranstaltung.through
        verbose_model = veranstaltung
    class BestandInLine(BestandModelBase):
        pass
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]
        
# ======================================================== Orte ========================================================

@admin.register(bundesland)
class BlandAdmin(ModelBase):
    search_fields = ['id', 'bland_name', 'code', 'land__land_name']
    list_display = ['bland_name', 'code', 'land']
    advanced_search_form = {
        'selects' : ['ort__land'], 
    }
    
@admin.register(land)
class LandAdmin(ModelBase):
    search_fields = ['id', 'land_name', 'code']
    crosslinks = ['ort']
    
@admin.register(kreis)
class KreisAdmin(ModelBase):
    pass
    
@admin.register(ort)
class OrtAdmin(ModelBase):
    fields = ['stadt', 'land', 'bland']
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name']
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    
    advanced_search_form = {
        'selects' : ['land', 'bland']
    }
    crosslinks = ['person', 'band', 'magazin', 'verlag', 'artikel', 'spielort', 'veranstaltung']
    
@admin.register(bestand)
class BestandAdmin(ModelBase):
    #readonly_fields = ['audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch', 'dokument', 'memorabilien', 'technik', 'video']
    list_display = ['signatur', 'bestand_art', 'lagerort','provenienz']
    #flds_to_group = [('ausgabe', 'ausgabe_magazin')]
    
    advanced_search_form = {
        'selects' : ['bestand_art', 'lagerort'], 
    }
    
@admin.register(provenienz)
class ProvAdmin(ModelBase):   
    pass
    
# Register your models here.
admin.site.register([buch_serie, monat, instrument, lagerort, geber, sender, sprache,  ])

