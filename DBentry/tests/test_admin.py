from django.urls import resolve

from .base import *

from DBentry.admin import *
from DBentry.sites import MIZAdminSite
from DBentry.forms import FormBase

class AdminTestMethodsMixin(object):
    
    crosslinks_relations = None
    crosslinks_object = None
    exclude_expected = None
    fields_expected = None
    
    def test_get_exclude(self):
        expected = self.exclude_expected or []
        self.assertEqual(self.model_admin.get_exclude(None), expected)
        
    def test_get_fields(self):
        expected = self.fields_expected or []
        self.assertEqual(self.model_admin.get_fields(self.get_request()), expected)
    
    def test_get_form(self):
        # form should be a subclass of FormBase, unless another form class was explicitly set on the ModelAdmin
        form = self.model_admin.get_form(self.get_request())
        self.assertTrue(issubclass(form, FormBase))
        
    def test_get_changelist(self):
        self.assertEqual(self.model_admin.get_changelist(self.get_request()), MIZChangeList)
    
    def test_get_search_fields(self):
        # search fields are declared with the models, the admin classes only add the exact =id lookup
        self.assertIn('=id', self.model_admin.get_search_fields())
    
    def test_get_search_fields_extra_pk(self):
        # An extra 'pk' search field was added, it should be replaced by an '=id' lookup
        request = self.get_request()
        self.model_admin.search_fields = ['pk']
        self.assertEqual(self.model_admin.get_search_fields(), ['=id'])
        
    def test_add_crosslinks(self):
        if self.crosslinks_object is None and not self.test_data:
            return
        obj = self.crosslinks_object or self.test_data[0]
        pk = str(obj.pk)
        links = self.model_admin.add_crosslinks(object_id=pk).get('crosslinks')
        if self.crosslinks_relations:
            self.assertEqual(len(links), len(self.crosslinks_relations))
            
            for rel in self.crosslinks_relations:
                count = 1
                if isinstance(rel, (list, tuple)):
                    rel, count = rel
                model_name = rel.related_model._meta.model_name
                fld_name = rel.remote_field.name
                url = reverse("admin:DBentry_{}_changelist".format(model_name)) \
                                        + "?" + fld_name + "=" + pk
                label = rel.related_model._meta.verbose_name_plural + " ({})".format(str(count))
                self.assertIn({'url':url, 'label':label}, links)
        else:
            self.assertEqual(len(links), 0)

class TestMIZModelAdmin(AdminTestCase):
    
    model_admin_class = DateiAdmin
    model = datei
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = datei.objects.create(titel='Testdatei')
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
    
    def test_get_actions(self):
        # No permissions: no actions
        actions = self.model_admin.get_actions(self.get_request(user=self.noperms_user))
        self.assertEqual(len(actions), 0)
        
        # staff_user has no permissions, so let's give him permission to delete artikel
        from django.contrib.auth.models import Permission
        p = Permission.objects.get(codename='delete_datei')
        self.staff_user.user_permissions.add(p)
        actions = self.model_admin.get_actions(self.get_request(user=self.staff_user))
        self.assertEqual(len(actions), 1)
        
        # superuser has all permissions inherently
        actions = self.model_admin.get_actions(self.get_request())
        self.assertEqual(len(actions), 2)   
        
    def test_group_fields(self):
        self.model_admin.fields = None
        self.assertEqual(self.model_admin.group_fields(), [])
        
        self.model_admin.fields = ['seite', 'ausgabe', 'schlagzeile', 'zusammenfassung', 'seitenumfang']
        self.model_admin.flds_to_group = [
            ('magazin', 'ausgabe'), ('xyz', 'abc'), ('schlagzeile', 'zusammenfassung'), ('seitenumfang', 'zusammenfassung')
        ]
        grouped_fields = self.model_admin.group_fields()
        
        # group_fields() should have ignored the nonsensical second tuple
        self.assertNotIn(('xyz', 'abc'), grouped_fields, msg='bad group was not removed')
        
        # the first tuple is expected to have replaced the 'ausgabe' in fields
        self.assertEqual(grouped_fields[1], ('magazin', 'ausgabe'))
        self.assertNotIn('ausgabe', grouped_fields, msg='field was not replaced')
        
        # by inserting the third tuple, group_fields() should have also removed the now redundant fourth field 'zusammenfassung'
        self.assertNotIn('zusammenfassung', grouped_fields, msg='redundant field not removed')
        
        # group_fields() must not add duplicate fields 
        self.assertNotIn(('seitenumfang', 'zusammenfassung'), grouped_fields, msg='group_fields() must not add duplicate fields')
                
    def test_add_extra_context(self):
        # no object_id passed in: add_crosslinks should not be called
        extra = self.model_admin.add_extra_context() 
        self.assertFalse('crosslinks' in extra)
    
    def test_add_view(self):
        response = self.client.get(self.add_path)
        self.assertTrue('collapse_all' in response.context)
        self.assertTrue('hint' in response.context)
        self.assertTrue('googlebtns' in response.context)
        self.assertFalse('crosslinks' in response.context) # no crosslinks allowed in add views
        
    def test_change_view(self):
        response = self.client.get(self.change_path.format(pk=self.obj1.pk))
        self.assertTrue('collapse_all' in response.context)
        self.assertTrue('hint' in response.context)
        self.assertTrue('googlebtns' in response.context)
        self.assertTrue('crosslinks' in response.context)
        
    def test_get_changeform_initial_data_no_initial(self):
        request = self.get_request()
        self.assertEqual(self.model_admin.get_changeform_initial_data(request), {})
        
    def test_get_changeform_initial_data_with_changelist_filters(self):
        initial = {'_changelist_filters':'ausgabe__magazin=326&q=asdasd&thisisbad'}
        request = self.get_request(data=initial)
        cf_init_data = self.model_admin.get_changeform_initial_data(request)
        self.assertTrue('ausgabe__magazin' in cf_init_data)
        self.assertEqual(cf_init_data.get('ausgabe__magazin'), '326')
        
    def test_get_inline_formsets(self):
        # no test needed
        pass
class TestAdminArtikel(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    exclude_expected = ['genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
    fields_expected = [
        ('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]
    test_data_count = 1
        
    def test_get_changeform_initial_data_with_changelist_filters(self):
        # ArtikelAdmin.get_changeform_initial_data makes sure 'magazin' is in initial for the form
        initial = {'_changelist_filters':'ausgabe__magazin=326&q=asdasd&thisisbad'}
        request = self.get_request(data=initial)
        cf_init_data = self.model_admin.get_changeform_initial_data(request)
        self.assertEqual(cf_init_data.get('magazin'), '326')

    @classmethod
    def setUpTestData(cls):
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.ausg = ausgabe.objects.create(magazin=cls.mag)
        cls.obj1 = artikel.objects.create(
            ausgabe = cls.ausg, seite = 1, schlagzeile = 'Test!'
        )
        
        s1 = schlagwort.objects.create(schlagwort = 'Testschlagwort1')
        s2 = schlagwort.objects.create(schlagwort = 'Testschlagwort2')
        artikel.schlagwort.through.objects.create(schlagwort = s1, artikel = cls.obj1)
        artikel.schlagwort.through.objects.create(schlagwort = s2, artikel = cls.obj1)
        
        m = musiker.objects.create(kuenstler_name='Alice Tester')
        b = band.objects.create(band_name='Testband')
        artikel.musiker.through.objects.create(musiker=m, artikel=cls.obj1)
        artikel.band.through.objects.create(band=b, artikel=cls.obj1)
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()

    def test_zusammenfassung_string(self):
        self.assertEqual(self.model_admin.zusammenfassung_string(self.obj1), '')
        self.obj1.zusammenfassung='Dies ist eine Testzusammenfassung, die nicht besonders lang ist.'
        self.assertEqual(self.model_admin.zusammenfassung_string(self.obj1), 'Dies ist eine Testzusammenfassung, die nicht [...]')

    def test_artikel_magazin(self):
        self.assertEqual(self.model_admin.artikel_magazin(self.obj1), self.mag)

    def test_schlagwort_string(self):
        self.assertEqual(self.model_admin.schlagwort_string(self.obj1), 'Testschlagwort1, Testschlagwort2')

    def test_kuenstler_string(self):
        self.assertEqual(self.model_admin.kuenstler_string(self.obj1), 'Testband, Alice Tester')

class TestAdminAusgabe(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    exclude_expected = ['audio']
    fields_expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
    
    crosslinks_relations = [ausgabe.artikel_set.rel]
   
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = ausgabe.objects.create(magazin=magazin.objects.create(magazin_name='Testmagazin'))
        artikel.objects.create(ausgabe=cls.obj1, schlagzeile='Test', seite=1)
        
        cls.obj1.ausgabe_jahr_set.create(jahr=2020)
        cls.obj1.ausgabe_jahr_set.create(jahr=2021)
        cls.obj1.ausgabe_jahr_set.create(jahr=2022)
        
        cls.obj1.ausgabe_num_set.create(num=10)
        cls.obj1.ausgabe_num_set.create(num=11)
        cls.obj1.ausgabe_num_set.create(num=12)
        
        cls.obj1.ausgabe_lnum_set.create(lnum=10)
        cls.obj1.ausgabe_lnum_set.create(lnum=11)
        cls.obj1.ausgabe_lnum_set.create(lnum=12)
        
        cls.obj1.ausgabe_monat_set.create(monat=monat.objects.create(id=1, monat='Januar', abk='Jan'))
        cls.obj1.ausgabe_monat_set.create(monat=monat.objects.create(id=2, monat='Februar', abk='Feb'))
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
    
    def test_group_fields(self):        
        # AusgabenAdmin flds_to_group = [('status', 'sonderausgabe')]
        expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
        request = self.get_request()
        fields = self.model_admin.get_fields(request)
        self.assertEqual(self.model_admin.group_fields(), expected)
        
    def test_anz_artikel(self):
        self.assertEqual(self.model_admin.anz_artikel(self.obj1), 1)
        artikel.objects.all().delete()
        self.assertEqual(self.model_admin.anz_artikel(self.obj1), 0)
        
    def test_jahr_string(self):
        self.assertEqual(self.model_admin.jahr_string(self.obj1), '2020, 2021, 2022')
        
    def test_num_string(self):
        self.assertEqual(self.model_admin.num_string(self.obj1), '10, 11, 12')
        
    def test_lnum_string(self):
        self.assertEqual(self.model_admin.lnum_string(self.obj1), '10, 11, 12')
        
    def test_monat_string(self):
        self.assertEqual(self.model_admin.monat_string(self.obj1), 'Jan, Feb')
        
class TestAdminMagazin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = MagazinAdmin
    model = magazin
    exclude_expected = ['genre']
    fields_expected = ['magazin_name', 'erstausgabe', 'turnus', 'magazin_url', 'ausgaben_merkmal', 'fanzine', 'issn', 
        'beschreibung', 'bemerkungen', 'verlag', 'ort', 
    ]
    
    crosslinks_relations = [magazin.ausgabe_set.rel]
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = magazin.objects.create(magazin_name='Testmagazin')
        ausgabe.objects.create(magazin=cls.obj1)
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
        
    def test_anz_ausgaben(self):
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 1)
        ausgabe.objects.all().delete()
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 0)


class TestAdminPerson(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = PersonAdmin
    model = person
    exclude_expected = ['orte']
    fields_expected = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    
    crosslinks_relations = [person.autor_set.rel, person.musiker_set.rel]
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = person.objects.create(vorname='Alice', nachname='Tester')
        musiker.objects.create(kuenstler_name='Beep', person=cls.obj1)
        autor.objects.create(person=cls.obj1)
        cls.obj2 = person.objects.create(vorname='Bob', nachname='Failure')
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super().setUpTestData()
    
    def test_Ist_Musiker(self):
        self.assertTrue(self.model_admin.Ist_Musiker(self.obj1))
        self.assertFalse(self.model_admin.Ist_Musiker(self.obj2))
        
    def test_Ist_Autor(self):
        self.assertTrue(self.model_admin.Ist_Autor(self.obj1))
        self.assertFalse(self.model_admin.Ist_Autor(self.obj2))

class TestAdminMusiker(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = MusikerAdmin
    model = musiker
    test_data_count = 1
    exclude_expected = ['genre', 'instrument', 'orte']
    fields_expected = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    
    crosslinks_relations = [
        dokument.musiker.rel, band.musiker.rel, artikel.musiker.rel, video.musiker.rel, bildmaterial.musiker.rel, 
        technik.musiker.rel, veranstaltung.musiker.rel, memorabilien.musiker.rel, buch.musiker.rel, 
        datei.musiker.rel, audio.musiker.rel, 
    ]
    
    @classmethod
    def setUpTestData(cls):
        # let the DataFactory set up obj1
        super().setUpTestData()
        
        cls.obj2 = musiker.objects.create(kuenstler_name='Test')
        b1 = band.objects.create(band_name='Testband1')
        musiker.band_set.through.objects.create(band=b1, musiker=cls.obj2)
        b2 = band.objects.create(band_name='Testband2')
        musiker.band_set.through.objects.create(band=b2, musiker=cls.obj2)
        
        g1 = genre.objects.create(genre='Testgenre1')
        musiker.genre.through.objects.create(genre=g1, musiker=cls.obj2)
        g2 = genre.objects.create(genre='Testgenre2')
        musiker.genre.through.objects.create(genre=g2, musiker=cls.obj2)
        
        cls.test_data.append(cls.obj2)
    
    def test_media_prop(self):
        self.assertTrue('admin/js/utils.js' in self.model_admin.media._js)
        
    def test_add_extra_context(self):
        extra = self.model_admin.add_extra_context(object_id=self.obj1.pk)
        self.assertTrue('crosslinks' in extra)
        
    def test_band_string(self):
        self.assertEqual(self.model_admin.band_string(self.obj2), 'Testband1, Testband2')
        
    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj2), 'Testgenre1, Testgenre2')
        
    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj2), '')
        o = ort.objects.create(stadt='Dortmund', land=land.objects.create(land_name='Testland', code='TE'))
        self.obj2.orte.add(o)
        self.obj2.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj2), 'Dortmund, TE')
        
class TestAdminGenre(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = GenreAdmin
    model = genre
    test_data_count = 1
    fields_expected = ['genre', 'ober']
    
    crosslinks_relations = [
        genre.musiker_set.rel, genre.datei_set.rel, genre.audio_set.rel, 
        genre.veranstaltung_set.rel, genre.bildmaterial_set.rel, genre.buch_set.rel, 
        genre.memorabilien_set.rel, genre.magazin_set.rel, genre.artikel_set.rel, genre.technik_set.rel, 
        genre.sub_genres.rel, genre.video_set.rel, genre.band_set.rel, genre.dokument_set.rel
    ]
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        cls.obj2 = genre.objects.create(genre='Topobject')
        cls.obj3 = genre.objects.create(genre='Subobject', ober=cls.obj2)
        cls.obj3.genre_alias_set.create(alias='Alias1')
        cls.obj3.genre_alias_set.create(alias='Alias2')
        
        cls.test_data.extend([cls.obj2, cls.obj3])
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Alias1')
        self.assertTrue(self.obj3 in result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertTrue(self.obj2 in result)
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj3), 'Alias1, Alias2')
        
    def test_ober_string(self):
        self.assertEqual(self.model_admin.ober_string(self.obj2), '')
        self.assertEqual(self.model_admin.ober_string(self.obj3), 'Topobject')
        
    def test_sub_string(self):
        self.assertEqual(self.model_admin.sub_string(self.obj2), 'Subobject')
        self.assertEqual(self.model_admin.sub_string(self.obj3), '')
    
class TestAdminSchlagwort(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = SchlagwortAdmin
    model = schlagwort
    test_data_count = 1
    fields_expected = ['schlagwort', 'ober']
    
    crosslinks_relations = [
        schlagwort.memorabilien_set.rel, schlagwort.artikel_set.rel, schlagwort.technik_set.rel, 
        schlagwort.datei_set.rel, schlagwort.video_set.rel, 
        schlagwort.dokument_set.rel, schlagwort.bildmaterial_set.rel, schlagwort.veranstaltung_set.rel, 
        schlagwort.unterbegriffe.rel, schlagwort.schlagwort_alias_set.rel, schlagwort.buch_set.rel, schlagwort.audio_set.rel
    ]
    
    @classmethod
    def setUpTestData(cls):
        super(TestAdminSchlagwort, cls).setUpTestData()
        
        cls.obj2 = schlagwort.objects.create(schlagwort='Topobject')
        cls.obj3 = schlagwort.objects.create(schlagwort='Subobject', ober=cls.obj2)
        cls.obj3.schlagwort_alias_set.create(alias='Alias1')
        cls.obj3.schlagwort_alias_set.create(alias='Alias2')
        
        cls.test_data.extend([cls.obj2, cls.obj3])
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Alias1')
        self.assertTrue(self.obj3 in result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertTrue(self.obj2 in result)
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj3), 'Alias1, Alias2')
        
    def test_ober_string(self):
        self.assertEqual(self.model_admin.ober_string(self.obj2), '')
        self.assertEqual(self.model_admin.ober_string(self.obj3), 'Topobject')
        
    def test_sub_string(self):
        self.assertEqual(self.model_admin.sub_string(self.obj2), 'Subobject')
        self.assertEqual(self.model_admin.sub_string(self.obj3), '')
    
class TestAdminBand(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = BandAdmin
    model = band
    exclude_expected = ['genre', 'musiker', 'orte']
    fields_expected = ['band_name', 'beschreibung', 'bemerkungen']
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = band.objects.create(band_name='Testband')
        band_alias.objects.create(alias='Alias1', parent=cls.obj1)
        band_alias.objects.create(alias='Alias2', parent=cls.obj1)
        
        g1 = genre.objects.create(genre='Testgenre1')
        band.genre.through.objects.create(genre=g1, band=cls.obj1)
        g2 = genre.objects.create(genre='Testgenre2')
        band.genre.through.objects.create(genre=g2, band=cls.obj1)
        
        m1 = musiker.objects.create(kuenstler_name='Testkuenstler1')
        band.musiker.through.objects.create(musiker=m1, band=cls.obj1)
        m2 = musiker.objects.create(kuenstler_name='Testkuenstler2')
        band.musiker.through.objects.create(musiker=m2, band=cls.obj1)
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj1), 'Alias1, Alias2')
        
    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj1), 'Testgenre1, Testgenre2')
        
    def test_musiker_string(self):
        self.assertEqual(self.model_admin.musiker_string(self.obj1), 'Testkuenstler1, Testkuenstler2')

class TestAdminAutor(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AutorAdmin
    model = autor
    exclude_expected = ['magazin']
    fields_expected = ['kuerzel', 'beschreibung', 'bemerkungen', 'person']
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = autor.objects.create(person=person.objects.create(vorname='Alice', nachname='Tester'))
        
        m2m_autor_magazin.objects.create(magazin=magazin.objects.create(magazin_name='Testmagazin1'), autor=cls.obj1)
        m2m_autor_magazin.objects.create(magazin=magazin.objects.create(magazin_name='Testmagazin2'), autor=cls.obj1)
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
        
    def test_magazin_string(self):
        self.assertEqual(self.model_admin.magazin_string(self.obj1), 'Testmagazin1, Testmagazin2')
        
class TestAdminOrt(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = OrtAdmin   
    model = ort
    fields_expected = ['stadt', 'land', 'bland']
    test_data_count = 1
    crosslinks_relations = [
        datei.ort.rel, buch.ort.rel, audio.ort.rel, ort.spielort_set.rel, ort.verlag_set.rel, ort.person_set.rel, 
        bildmaterial.ort.rel, dokument.ort.rel, artikel.ort.rel, ort.magazin_set.rel, technik.ort.rel, 
        ort.band_set.rel, memorabilien.ort.rel, 
    ]
    
        
class TestAdminLand(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = LandAdmin
    model = land
    fields_expected = ['land_name', 'code']
    test_data_count = 1
    crosslinks_relations = [
        land.ort_set.rel, land.bundesland_set.rel, 
    ]
        
class TestAdminBundesland(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = BlandAdmin
    model = bundesland
    fields_expected = ['bland_name', 'code', 'land']
    test_data_count = 1
    crosslinks_relations = [
        bundesland.kreis_set.rel, 
    ]
        
class TestAdminInstrument(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = InstrumentAdmin
    model = instrument
    fields_expected = ['instrument', 'kuerzel']
    test_data_count = 1
    crosslinks_relations = [
        instrument.musiker_set.rel, 
    ]
    
class TestAdminAudio(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AudioAdmin
    model = audio
    exclude_expected = ['plattenfirma', 'band', 'genre', 'musiker', 'person', 'schlagwort', 'spielort', 'veranstaltung', 'ort']
    # Note that AudioAdmin specifies a fieldsets attribute, overriding (and removing catalog_nr) the fields for the form that way
    fields_expected = ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'catalog_nr',
        'release_id', 'discogs_url', 'beschreibung', 'bemerkungen', 'sender'
    ]
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = audio.objects.create(titel='Testaudio')
        cls.test_data = [cls.obj1]

        super().setUpTestData()

    def test_kuenstler_string(self):
        m = musiker.objects.create(kuenstler_name='Alice Tester')
        self.model.musiker.through.objects.create(musiker=m, audio=self.obj1)
        b = band.objects.create(band_name='Testband')
        self.model.band.through.objects.create(band=b, audio=self.obj1)
        self.assertEqual(self.model_admin.kuenstler_string(self.obj1), 'Testband, Alice Tester')

    def test_formate_string(self):
        ft = FormatTyp.objects.create(typ='TestTyp1')
        Format.objects.create(format_typ=ft, audio=self.obj1)
        ft = FormatTyp.objects.create(typ='TestTyp2')
        Format.objects.create(format_typ=ft, audio=self.obj1)
        # format_name is a non-editable field (compiled of the Format's properties), its use is mainly for autocomplete searches
        # any format_name set manually should be overriden by Format.get_name()
        self.assertEqual(self.model_admin.formate_string(self.obj1), 'TestTyp1, TestTyp2')
    
class TestAdminSpielort(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = SpielortAdmin
    model = spielort
    fields_expected = ['name', 'ort']
    crosslinks_relations = [
        spielort.dokument_set.rel, spielort.spielort_alias_set.rel, spielort.m2m_audio_spielort_set.rel,
        spielort.artikel_set.rel, spielort.buch_set.rel, spielort.bildmaterial_set.rel,
        spielort.video_set.rel, spielort.datei_set.rel, spielort.veranstaltung_set.rel,
        spielort.audio_set.rel, spielort.technik_set.rel, spielort.m2m_artikel_spielort_set.rel,
        spielort.memorabilien_set.rel,
        ]
    test_data_count = 1
        
class TestAdminVeranstaltung(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = VeranstaltungAdmin
    model = veranstaltung
    exclude_expected = ['genre', 'person', 'band', 'schlagwort', 'musiker']
    fields_expected = ['name', 'datum', 'spielort']
    test_data_count = 1
    
class TestAdminBuch(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = BuchAdmin
    model = buch
    exclude_expected = ['autor', 'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
    fields_expected = ['titel', 'titel_orig', ('jahr', 'verlag'), ('jahr_orig', 'verlag_orig'), 
            'ausgabe', 'auflage', 'buch_band', 
            'ubersetzer', ('EAN', 'ISBN'), 'LCCN', 
            'beschreibung', 'bemerkungen', 
            'buch_serie', ('sprache', 'sprache_orig'), 
        ]
    test_data_count = 1

    def test_group_fields(self):        
        # BuchAdmin flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
        expected = ['titel', 'titel_orig', ('jahr', 'verlag'), ('jahr_orig', 'verlag_orig'), 
            'ausgabe', 'auflage', 'buch_serie', 'buch_band', 
            ('sprache', 'sprache_orig'), 'ubersetzer', ('EAN', 'ISBN'), 'LCCN'
        ]
        request = self.get_request()
        fields = self.model_admin.get_fields(request)
        self.assertEqual(self.model_admin.group_fields(), self.fields_expected)
        
    
class TestAdminSite(UserTestCase):
    
    def test_app_index(self):
        response = self.client.get('/admin/DBentry/')
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.app_index.__name__)
        request = response.wsgi_request
        
        response = self.client.get('/admin/')
        request = response.wsgi_request
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.index.__name__)
        
    def test_index_DBentry(self):
        request = self.client.get('/admin/').wsgi_request
        response = miz_site.index(request)
        app_list = response.context_data['app_list']
        
        # check if there are two 'categories' (fake apps) for app DBentry (app_list was extended by two new app_dicts)
        app_names = [d.get('name','') for d in app_list]
        self.assertTrue('Hauptkategorien' in app_names)
        self.assertTrue('Nebenkategorien' in app_names)
        
    def test_index_admintools(self):
        from DBentry.bulk.views import BulkAusgabe
        tool = BulkAusgabe
        miz_site.register_tool(tool)
        
        request = self.client.get('/admin/').wsgi_request
        response = miz_site.index(request)
        
        self.assertTrue('admintools' in response.context_data)
        
    def test_get_admin_model(self):
        expected_model_admin = ArtikelAdmin
        self.assertIsInstance(miz_site.get_admin_model(artikel), expected_model_admin)
        self.assertIsInstance(miz_site.get_admin_model('DBentry.artikel'), expected_model_admin)
        self.assertIsNone(miz_site.get_admin_model('BEEP.BOOP'))
        
# ChangeList uses ModelAdmin attributes, so test this last
from DBentry.changelist import *
class TestChangeList(AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    test_data_count = 3
    
    def setUp(self):
        super(TestChangeList, self).setUp()
        self.init_data = dict(
            model = self.model, 
            list_display = self.model_admin.list_display, 
            list_display_links = self.model_admin.list_display_links, 
            list_filter = self.model_admin.list_filter, 
            date_hierarchy = self.model_admin.date_hierarchy, 
            search_fields = self.model_admin.search_fields, 
            list_select_related = self.model_admin.list_select_related,
            list_per_page = self.model_admin.list_per_page, 
            list_max_show_all = self.model_admin.list_max_show_all, 
            list_editable = self.model_admin.list_editable, 
            model_admin = self.model_admin
        )
    
    def get_cl(self, data={}):
        request = self.get_request(path=self.changelist_path, data=data)
        return MIZChangeList(request, **self.init_data.copy())
        
    def test_init(self):
        cl = self.get_cl()
        self.assertTrue(hasattr(cl, 'request'))
    
    def test_init_pagevar(self):
        # show that MIZChangeList can handle the PAGE_VAR
        request = self.get_request(path=self.changelist_path, data={'p':['1']})
        with self.assertNotRaises(IncorrectLookupParameters):
            MIZChangeList(request, **self.init_data.copy())
    
    def test_init_errorvar(self):
        # show that MIZChangeList can handle the ERROR_FLAG
        request = self.get_request(path=self.changelist_path, data={'e':['1']})
        with self.assertNotRaises(IncorrectLookupParameters):
            MIZChangeList(request, **self.init_data.copy())
    
    def test_get_filters(self):
        request_data = dict(genre = [1, 2])
        cl = self.get_cl(request_data)
        (filter_specs, has_filters, remaining_lookup_params, use_distinct) = cl.get_filters(cl.request)
        
    def test_get_filters_empty_params(self):
        cl = self.get_cl()
        expected = ( [], False, {}, False )
        self.assertEqual(cl.get_filters(cl.request), expected)
        
    def test_get_filters_DisallowedModelAdminLookup(self):
        #NOTE: Cannot test this as every lookup seems to be allowed.
        pass
        
    def test_get_filters_with_list_filters(self):
        #NOTE: Cannot test this as we're not using any list_filters ever.
        pass
        
    def test_get_filters_build_remaining_lookup_params(self):
        pass
        
    def test_get_filters_FieldDoesNotExist(self):
        cl = self.get_cl()
        request_data = dict(beep = 'boop')
        request = self.get_request(path=self.changelist_path, data=request_data)
        
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_filters(request)
            
    def test_get_queryset(self):
        pass

    def test_get_queryset_qs_redirect(self):
        session = self.client.session
        ids = [i.pk for i in self.test_data]
        session['qs'] = dict(id__in=ids)
        session.save()
        
        cl = self.get_cl()
        cl_qs = cl.get_queryset(cl.request).order_by('pk')
        expected_qs =  self.model.objects.filter(**dict(id__in=ids)).order_by('pk')
        self.assertListEqual(list(cl_qs), list(expected_qs))
        
    def test_get_queryset_IncorrectLookupParameters(self):
        cl = self.get_cl()
        request_data = dict(
            genre = ['a', 'b'] # should be int
        )
        request = self.get_request(path=self.changelist_path, data=request_data)
        
        with self.assertRaises(IncorrectLookupParameters):
            cl.get_queryset(request)
