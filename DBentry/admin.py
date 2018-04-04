
from collections import OrderedDict

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse, resolve
from django.shortcuts import redirect
from django.contrib.auth import get_permission_codename

from .models import *
from .forms import makeForm, InLineAusgabeForm
from .utils import link_list, concat_limit
from .changelist import MIZChangeList
from .actions import *

from .sites import miz_site

MERGE_DENIED_MSG = 'Die ausgewählten {} gehören zu unterschiedlichen {}{}.'


class ModelBase(admin.ModelAdmin):
    
    def __init__(self, *args, **kwargs):
        super(ModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(self.model)
        
    search_fields_redirect = dict()
    flds_to_group = []
    googlebtns = []
    collapse_all = False                    # Whether to collapse all inlines/fieldsets by default or not
    hint = ''                               # A hint displayed at the top of the form 
    actions = [merge_records]

    def has_adv_sf(self):
        return len(getattr(self, 'advanced_search_form', []))>0
    
    def get_changelist(self, request, **kwargs):
        return MIZChangeList
        
    def get_actions(self, request):
        # Show actions based on user permissions
        actions = super(ModelBase, self).get_actions(request) #= OrderedDict( (name, (func, name, desc)) )
        
        #TODO: use ActionConfirmationView + MIZAdminPermissionMixin permission_test() to unify all the things?
        for func, name, desc in actions.values():
            if name == 'delete_selected':
                perm_required = ['delete'] # the builtin action delete_selected is set by the admin site
            else:
                perm_required = getattr(func, 'perm_required', [])
            
            for p in perm_required:
                perm_passed = False
                if callable(p):
                    perm_passed = p(self, request)
                else:
                    perm = '{}.{}'.format(self.opts.app_label, get_permission_codename(p, self.opts))
                    perm_passed = request.user.has_perm(perm)
                if not perm_passed:
                    del actions[name]
        return actions
        
    def get_exclude(self, request, obj = None):
        #TODO: if not fld is reverse relation 
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
        if not self.fields:
            return []
        grouped_fields = self.fields
        for tpl in self.flds_to_group:
            # Find the correct spot to insert the tuple into:
            # which would be the earliest occurence of any field of tuple in self.fields
            indexes = [self.fields.index(i) for i in tpl if i in self.fields]
            if not indexes:
                # None of the fields in the tuple are actually in self.fields
                continue
            target_index = min(indexes)
            grouped_fields[target_index] = tpl
            indexes.remove(target_index)
            # Remove all other fields of the tuple that are in self.fields
            for i in indexes:
                grouped_fields.pop(i)
        return grouped_fields
    
    def get_search_fields(self, request=None):
        search_fields = self.search_fields or list(self.model.get_search_fields())
        # add __exact for pk lookups
        pk_name = self.model._meta.pk.name
        if "=" + pk_name in search_fields:
            pass
        elif pk_name in search_fields:
            search_fields.remove(pk_name)
            search_fields.append("=" + pk_name)
        else:
            search_fields.append("=" + pk_name)
        return search_fields
        
    def add_crosslinks(self, object_id):
        new_extra = {}
        new_extra['crosslinks'] = []
        
        inlmdls = {i.model for i in self.inlines}
        for rel in self.opts.related_objects:
            if rel.many_to_many or rel.one_to_many:
                model = rel.related_model
                fld_name = rel.remote_field.name
                if model in inlmdls:
                    continue
                count = model.objects.filter(**{fld_name:object_id}).count()
                if not count:
                    continue
                try:
                    link = reverse("admin:{}_{}_changelist".format(self.opts.app_label, model._meta.model_name)) \
                                    + "?" + fld_name + "=" + str(object_id)
                except Exception as e:
                    #TODO: proper exception class
                    # No reverse match found
                    continue
                label = model._meta.verbose_name_plural + " ({})".format(str(count))
                new_extra['crosslinks'].append( dict(link=link, label=label) )
        return new_extra
        
    @property
    def media(self):
        media = super(ModelBase, self).media
        if self.googlebtns:
            media.add_js(['admin/js/utils.js'])
        return media
        
    def add_extra_context(self, extra_context = None, object_id = None):
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id))
        new_extra['collapse_all'] = self.collapse_all
        new_extra['hint'] = self.hint
        new_extra['googlebtns'] = self.googlebtns
        return new_extra
        
    def add_view(self, request, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context)
        return self.changeform_view(request, None, form_url, new_extra)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context, object_id)
        return super(ModelBase, self).change_view(request, object_id, form_url, new_extra)
        
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
            IMPORTANT: THIS ONLY GOVERNS FORMFIELDS FOR ADD-VIEWS. 
            Primarily used for setting ausgabe/magazin for Artikel add-views.
        """
        from django.utils.http import unquote
        initial = super(ModelBase, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys() or not initial['_changelist_filters']:
            return initial
            
        # At this point, _changelist_filters is a string of format:
        # '_changelist_filters': 'ausgabe__magazin=47&ausgabe=4288'
        # SEARCH_TERM_SEP: '='
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
        
    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        # Add a description to each formset
        inline_admin_formsets = super(ModelBase, self).get_inline_formsets(request, formsets, inline_instances, obj)
        for formset in inline_admin_formsets:
            formset.description = getattr(formset.opts, 'description', '')
        return inline_admin_formsets
        
    def merge_allowed(self, request, queryset):
        """ Hook for checks on merging. """
        #TODO: move this to actions.py
        return True
        
class TabModelBase(admin.TabularInline):
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        super(TabModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural
            
class StackModelBase(admin.StackedInline):
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        super(StackModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural

class AliasTabBase(TabModelBase):
    verbose_name_plural = 'Alias'
    
class BestandInLine(TabModelBase):
    model = bestand
    readonly_fields = ['signatur']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = bestand._meta.verbose_name
    verbose_name_plural = bestand._meta.verbose_name_plural
    
class GenreModelBase(TabModelBase):
    extra = 1
    verbose_name = genre._meta.verbose_name
    verbose_name_plural = genre._meta.verbose_name_plural
    
class SchlagwortModelBase(TabModelBase):
    extra = 1
    verbose_name = schlagwort._meta.verbose_name
    verbose_name_plural = schlagwort._meta.verbose_name_plural
    
class DateiInLine(TabModelBase):
    model = m2m_datei_quelle
    verbose_model = datei
    fields = ['datei']

class QuelleInLine(StackModelBase):
    extra = 0
    model = m2m_datei_quelle
    description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'
    
class AusgabeInLineBase(admin.TabularInline):
    model = None
    fields = ['magazin', 'ausgabe']
    original = False
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        self.form = InLineAusgabeForm
        super(AusgabeInLineBase, self).__init__(*args, **kwargs)
        self.verbose_name = ausgabe._meta.verbose_name
        self.verbose_name_plural = ausgabe._meta.verbose_name_plural
        
        
@admin.register(audio, site=miz_site)
class AudioAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = audio.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = audio.schlagwort.through
    class PersonInLine(TabModelBase):
        model = audio.person.through
        verbose_model = person
    class MusikerInLine(StackModelBase):
        model = audio.musiker.through
        verbose_model = musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(TabModelBase):
        model = audio.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = audio.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = audio.veranstaltung.through
        verbose_model = veranstaltung
    class FormatInLine(StackModelBase):
        model = Format
        extra = 0
        filter_horizontal = ['tag']
        fieldsets = [
            (None, {'fields' : ['anzahl', 'format_typ', 'format_size', 'catalog_nr', 'tape', 'channel', 'noise_red']}), 
            ('Tags', {'fields' : ['tag'], 'classes' : ['collapse', 'collapsed']}), 
            ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class OrtInLine(TabModelBase):
        model = audio.ort.through
        verbose_model = ort
    class PlattenInLine(TabModelBase):
        model = audio.plattenfirma.through
        verbose_model = plattenfirma
    class AusgabeInLine(AusgabeInLineBase):
        model = ausgabe.audio.through
    inlines = [PlattenInLine, FormatInLine, DateiInLine, MusikerInLine, BandInLine, GenreInLine, SchlInLine, 
            VeranstaltungInLine, SpielortInLine, OrtInLine, PersonInLine, BestandInLine, AusgabeInLine]
    fieldsets = [
        (None, {'fields' : ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'sender']}), 
        ('Discogs', {'fields' : ['release_id', 'discogs_url'], 'classes' : ['collapse', 'collapsed']}), 
        ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
    ]
    list_display = ['__str__', 'formate_string', 'kuenstler_string']
    save_on_top = True
    collapse_all = True
    
    advanced_search_form = {
        'selects' : ['musiker', 'band', 'genre', 'spielort', 'veranstaltung', 'plattenfirma', 
                        'format__format_size', 'format__format_typ', 'format__tag'], 
        'simple' : ['release_id'], 
        'labels' : {'format__tag':'Tags'}, 
    }
    
    
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

@admin.register(ausgabe, site=miz_site)
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
    class AudioInLine(TabModelBase):
        model = ausgabe.audio.through
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine, AudioInLine]
    flds_to_group = [('status', 'sonderausgabe')]
    
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahr_string', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
                            
    actions = [bulk_jg, add_bestand]
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum'], 
        'selects':['magazin','status'], 
        'simple':['jahrgang', 'sonderausgabe']
    }
                
    def anz_artikel(self, obj):
        return obj.artikel_set.count()
    anz_artikel.short_description = 'Anz. Artikel'
    
    def jahr_string(self, obj):
        return concat_limit(obj.ausgabe_jahr_set.all())
    jahr_string.short_description = 'Jahre'
    
    def num_string(self, obj):
        return concat_limit(obj.ausgabe_num_set.all())
    num_string.short_description = 'Nummer'
    
    def lnum_string(self, obj):
        return concat_limit(obj.ausgabe_lnum_set.all())
    lnum_string.short_description = 'lfd. Nummer'
    
    def monat_string(self, obj):
        if obj.ausgabe_monat_set.exists():
            return concat_limit(obj.ausgabe_monat_set.values_list('monat__abk', flat=True))
    monat_string.short_description = 'Monate'
    
    def zbestand(self, obj):
        return obj.bestand_set.filter(lagerort=lagerort.objects.filter(pk=ZRAUM_ID)).exists()
    zbestand.short_description = 'Bestand: ZRaum'
    zbestand.boolean = True
    
    def dbestand(self, obj):
        return obj.bestand_set.filter(lagerort=lagerort.objects.filter(pk=DUPLETTEN_ID)).exists()
    dbestand.short_description = 'Bestand: Dublette'
    dbestand.boolean = True
    
    
@admin.register(autor, site=miz_site)
class AutorAdmin(ModelBase):
    class MagazinInLine(TabModelBase):
        model = autor.magazin.through
        extra = 1
    
    inlines = [MagazinInLine]
    
    list_display = ['__str__', 'magazin_string']

    advanced_search_form = {
        'selects' : ['magazin']
    }
            
    def magazin_string(self, obj):
        return concat_limit(obj.magazin.all())
    magazin_string.short_description = 'Magazin(e)'
    
@admin.register(artikel, site=miz_site)
class ArtikelAdmin(ModelBase):  
    class GenreInLine(GenreModelBase):
        model = artikel.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = artikel.schlagwort.through
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
    flds_to_group = [('magazin', 'ausgabe'),('seite', 'seitenumfang'),]
    
    list_display = ['__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string','ausgabe','artikel_magazin', 'kuenstler_string']
    list_display_links = ['__str__', 'seite']
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', ('ausgabe', 'ausgabe__magazin'), 'schlagwort', 'genre', 'band', 'musiker', 'autor'], 
        'simple':[], 
    }  
    save_on_top = True

    def get_queryset(self, request):
        # NOTE: resultbased_ordering?
        from django.db.models import Min
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite', 'pk')
        return qs
        
@admin.register(band, site=miz_site)    
class BandAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = band.genre.through
    class MusikerInLine(TabModelBase):
        model = band.musiker.through
    class AliasInLine(AliasTabBase):
        model = band_alias
    save_on_top = True
    inlines=[GenreInLine, AliasInLine, MusikerInLine]
    
    list_display = ['band_name', 'genre_string', 'herkunft', 'musiker_string']

    googlebtns = ['band_name']
    
    advanced_search_form = {
        'selects' : ['musiker', 'genre', 'herkunft__land', 'herkunft'], 
        'labels' : {'musiker':'Mitglied','herkunft__land':'Herkunftsland', 'herkunft':'Herkunftsort'}
    }
        
    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'
        
    def musiker_string(self, obj):
        return concat_limit(obj.musiker.all())
    musiker_string.short_description = 'Mitglieder'
    
    def alias_string(self, obj):
        return concat_limit(obj.band_alias_set.all())
    alias_string.short_description = 'Aliase'
    
@admin.register(bildmaterial, site=miz_site)
class BildmaterialAdmin(ModelBase):
    pass
    
@admin.register(buch, site=miz_site)
class BuchAdmin(ModelBase):
    class AutorInLine(TabModelBase):
        model = buch.autor.through
        verbose_model = autor
    save_on_top = True
    inlines = [AutorInLine, BestandInLine]
    flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
    search_fields = ['pk','titel']
    advanced_search_form = {
        'selects' : ['verlag', 'sprache'], 
        'simple' : [], 
        'labels' : {}, 
    }
    
@admin.register(dokument, site=miz_site)
class DokumentAdmin(ModelBase):
    infields = [BestandInLine]
    
@admin.register(genre, site=miz_site)
class GenreAdmin(ModelBase):
    class AliasInLine(AliasTabBase):
        model = genre_alias
    inlines = [AliasInLine]
    list_display = ['genre', 'alias_string', 'ober_string']
        
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Obergenre'
        
    def alias_string(self, obj):
        return concat_limit(obj.genre_alias_set.all())
    alias_string.short_description = 'Aliase'
    

@admin.register(magazin, site=miz_site)
class MagazinAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = magazin.genre.through
        magazin.genre.through.verbose_name = ''
    inlines = [GenreInLine]
    
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    
    advanced_search_form = {
        'selects' : ['ort__land'], 
        'labels' : {'ort__land':'Herausgabeland'}
    }
        
    def anz_ausgaben(self, obj):
        return obj.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'

@admin.register(memorabilien, site=miz_site)
class MemoAdmin(ModelBase):
    inlines = [BestandInLine]

@admin.register(musiker, site=miz_site)
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
    readonly_fields = ['band_string', 'genre_string', 'herkunft_string']
    fields = ['kuenstler_name', ('person', 'herkunft_string'), 'beschreibung']
    
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'herkunft_string']
    
    googlebtns = ['kuenstler_name']
    
    advanced_search_form = {
        'selects' : ['person', 'genre', 'band', 
                'instrument','person__herkunft__land', 'person__herkunft'], 
        'labels' : {'person__herkunft__land':'Herkunftsland'}
    }
        
    def band_string(self, obj):
        return concat_limit(obj.band_set.all())
    band_string.short_description = 'Bands'
    
    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'
    
    def herkunft_string(self, obj):
        if obj.person and obj.person.herkunft:
            return str(obj.person.herkunft)
        else:
            return '---'
    herkunft_string.short_description = 'Herkunft'
    
@admin.register(person, site=miz_site)
class PersonAdmin(ModelBase):
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    fields = ['vorname', 'nachname', 'herkunft', 'beschreibung']
    
    advanced_search_form = {
        'selects' : ['herkunft', 'herkunft__land', ('herkunft__bland', 'herkunft__land')]
    }
    
    def Ist_Musiker(self, obj):
        return obj.musiker_set.exists()
    Ist_Musiker.boolean = True
    
    def Ist_Autor(self, obj):
        return obj.autor_set.exists()
    Ist_Autor.boolean = True
    
@admin.register(schlagwort, site=miz_site)
class SchlagwortAdmin(ModelBase):
    class AliasInLine(AliasTabBase):
        model = schlagwort_alias
        extra = 1
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string', 'ober_string']
        
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Oberbegriff'
        
    def alias_string(self, obj):
        return concat_limit(obj.schlagwort_alias_set.all())
    alias_string.short_description = 'Aliase'
    
@admin.register(spielort, site=miz_site)
class SpielortAdmin(ModelBase):
    list_display = ['name', 'ort']
    
@admin.register(technik, site=miz_site)
class TechnikAdmin(ModelBase):
    inlines = [BestandInLine]

@admin.register(veranstaltung, site=miz_site)
class VeranstaltungAdmin(ModelBase):
    #TODO: finish this
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
    
@admin.register(verlag, site=miz_site)
class VerlagAdmin(ModelBase):
    list_display = ['verlag_name', 'sitz']
    advanced_search_form = {
        'selects' : ['sitz','sitz__land', 'sitz__bland'], 
        'labels' : {'sitz':'Sitz'}
    }
    
        
@admin.register(video, site=miz_site)
class VideoAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = video.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = video.schlagwort.through
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
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]
        
# ======================================================== Orte ========================================================

@admin.register(bundesland, site=miz_site)
class BlandAdmin(ModelBase):
    list_display = ['bland_name', 'code', 'land']
    advanced_search_form = {
        'selects' : ['ort__land'], 
    }
    
@admin.register(land, site=miz_site)
class LandAdmin(ModelBase):
    pass
    
@admin.register(kreis, site=miz_site)
class KreisAdmin(ModelBase):
    pass
    
@admin.register(ort, site=miz_site)
class OrtAdmin(ModelBase):
    fields = ['stadt', 'land', 'bland']
    
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    
    advanced_search_form = {
        'selects' : ['land', 'bland']
    }
    
@admin.register(bestand, site=miz_site)
class BestandAdmin(ModelBase):
    #readonly_fields = ['audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch', 'dokument', 'memorabilien', 'technik', 'video']
    list_display = ['signatur', 'bestand_art', 'lagerort','provenienz']
    #flds_to_group = [('ausgabe', 'ausgabe_magazin')]
    
    advanced_search_form = {
        'selects' : ['bestand_art', 'lagerort'], 
    }
    
@admin.register(provenienz, site=miz_site)
class ProvAdmin(ModelBase):   
    pass
      
@admin.register(datei, site=miz_site)
class DateiAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = datei.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = datei.schlagwort.through
    class PersonInLine(TabModelBase):
        model = datei.person.through
        verbose_model = person
    class MusikerInLine(StackModelBase):
        model = datei.musiker.through
        verbose_model = musiker
        filter_horizontal = ['instrument']
    class BandInLine(TabModelBase):
        model = datei.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = datei.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = datei.veranstaltung.through
        verbose_model = veranstaltung
    inlines = [QuelleInLine, BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine]
    fieldsets = [
        (None, { 'fields': ['titel', 'media_typ', 'datei_pfad', 'provenienz']}),
        ('Allgemeine Beschreibung', { 'fields' : ['beschreibung', 'datum', 'quelle', 'sender', 'bemerkungen']}),  
    ]
    save_on_top = True
    collapse_all = True
    hint = 'Diese Seite ist noch nicht vollständig fertig gestellt. Bitte noch nicht benutzen.'
    
@admin.register(instrument, site=miz_site)
class InstrumentAdmin(ModelBase):
    list_display = ['instrument', 'kuerzel']

# Register your models here.

miz_site.register([buch_serie, monat, lagerort, geber, sender, sprache, plattenfirma])

miz_site.register([Format, FormatTag, FormatSize, FormatTyp, NoiseRed])
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
miz_site.register(Group, GroupAdmin)
miz_site.register(User, UserAdmin)
