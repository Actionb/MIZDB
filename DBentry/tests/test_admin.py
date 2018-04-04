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

class TestMIZModelAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    test_data_count = 3
    exclude_expected = ['genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
    fields_expected = [('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'info']
    
    def test_get_actions(self):
        # No permissions: no actions
        actions = self.model_admin.get_actions(self.get_request(user=self.noperms_user))
        self.assertEqual(len(actions), 0)
        
        # staff_user has no permissions, so let's give him permission to delete artikel
        from django.contrib.auth.models import Permission
        p = Permission.objects.get(codename='delete_artikel')
        self.staff_user.user_permissions.add(p)
        actions = self.model_admin.get_actions(self.get_request(user=self.staff_user))
        self.assertEqual(len(actions), 1)
        
        # superuser has all permissions inherently
        actions = self.model_admin.get_actions(self.get_request())
        self.assertEqual(len(actions), 2)
        
    def test_get_form(self):
        request = self.get_request(path=self.add_path)
        form = self.model_admin.get_form(request)
        # test if 'magazin' gets wrapped
        from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

        self.assertIsInstance(form.declared_fields['magazin'].widget, RelatedFieldWidgetWrapper)
        
    def test_group_fields(self):
        request = self.get_request()
        fields = self.model_admin.get_fields(request) # sets model_admin.fields
        self.model_admin.fields = None
        self.assertEqual(self.model_admin.group_fields(), [])
        
        # ArtikelAdmin flds_to_group = [('magazin', 'ausgabe'),('seite', 'seitenumfang'),]
        expected = [('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'info']
        self.model_admin.fields = fields
        self.assertEqual(self.model_admin.group_fields(), expected)
        
    def test_media_prop(self):
        # nothing to test for artikel
        pass
        
    def test_add_extra_context(self):
        # artikel can't actually have any crosslinks
        extra = self.model_admin.add_extra_context() # no object_id passed in: add_crosslinks should not be called
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
        
    def test_lookup_allowed(self):
        # Errr... this ALWAYS returns True
        self.assertTrue(self.model_admin.lookup_allowed(key='band', value=None))
#        self.assertFalse(self.model_admin.lookup_allowed(key='beep_boop', value=None))
        
    def test_get_changeform_initial_data_no_initial(self):
        request = self.get_request()
        self.assertEqual(self.model_admin.get_changeform_initial_data(request), {})
        
    def test_get_changeform_initial_data_unimportant_initial(self):
        initial = {'beep':'boop'}
        request = self.get_request(data=initial)
        self.assertEqual(self.model_admin.get_changeform_initial_data(request), initial)
        
    def test_get_changeform_initial_data_with_changelist_filters(self):
        initial = {'_changelist_filters':'ausgabe__magazin=326&q=asdasd&thisisbad'}
        request = self.get_request(data=initial)
        cf_init_data = self.model_admin.get_changeform_initial_data(request)
        self.assertTrue('ausgabe__magazin' in cf_init_data)
        self.assertEqual(cf_init_data.get('ausgabe__magazin'), '326')
        
    def test_get_inline_formsets(self):
        # no test needed
        pass

class TestAdminAusgabe(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    exclude_expected = ['audio']
    fields_expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'info']
    
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
        expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'info']
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
    fields_expected = ['magazin_name', 'info', 'erstausgabe', 'turnus', 'magazin_url', 'beschreibung', 'ausgaben_merkmal', 
        'verlag', 'ort', 
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
    fields_expected = ['vorname', 'nachname', 'herkunft', 'beschreibung']
    
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
    exclude_expected = ['genre', 'instrument']
    fields_expected = ['kuenstler_name', ('person', 'herkunft_string'), 'beschreibung']
    
    crosslinks_relations = [artikel.musiker.rel, audio.musiker.rel, video.musiker.rel, datei.musiker.rel, band.musiker.rel]
    
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
        
    def test_herkunft_string(self):
        self.assertEqual(self.model_admin.herkunft_string(self.obj2), '---')
        o = ort.objects.create(stadt='Dortmund', land=land.objects.create(land_name='Testland', code='TE'))
        p = person.objects.create(vorname='Alice', nachname='Tester', herkunft=o)
        self.qs_obj2.update(person=p)
        self.obj2.refresh_from_db()
        self.assertEqual(self.model_admin.herkunft_string(self.obj2), 'Dortmund, TE')
        
class TestAdminGenre(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = GenreAdmin
    model = genre
    test_data_count = 1
    fields_expected = ['genre', 'ober']
    
    crosslinks_relations = [band.genre.rel, musiker.genre.rel, magazin.genre.rel, artikel.genre.rel, audio.genre.rel, 
            veranstaltung.genre.rel, video.genre.rel, datei.genre.rel]
    
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
        
    
class TestAdminSchlagwort(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = SchlagwortAdmin
    model = schlagwort
    test_data_count = 1
    fields_expected = ['schlagwort', 'ober']
    
    crosslinks_relations = [artikel.schlagwort.rel, audio.schlagwort.rel, video.schlagwort.rel, datei.schlagwort.rel]
    
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
        self.assertEqual(self.model_admin.ober_string(self.obj3), 'Topobject')
    
class TestAdminBand(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = BandAdmin
    model = band
    exclude_expected = ['genre', 'musiker']
    fields_expected = ['band_name', 'herkunft', 'beschreibung']
    
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
    fields_expected = ['kuerzel', 'person']
    
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
        
class TestAdminLand(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = LandAdmin
    model = land
    fields_expected = ['land_name', 'code']
        
class TestAdminBundesland(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = BlandAdmin
    model = bundesland
    fields_expected = ['bland_name', 'code', 'land']
        
class TestAdminInstrument(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = InstrumentAdmin
    model = instrument
    fields_expected = ['instrument', 'kuerzel']
    
class TestAdminAudio(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AudioAdmin
    model = audio
    exclude_expected = ['plattenfirma', 'band', 'genre', 'musiker', 'person', 'schlagwort', 'spielort', 'veranstaltung', 'ort']
    # Note that AudioAdmin specifies a fieldsets attribute, overriding (and removing catalog_nr) the fields for the form that way
    fields_expected = ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'sender', 'catalog_nr',
        'release_id', 'discogs_url', 'bemerkungen', 
    ]
    
@skip('SenderAdmin not yet implemented')
class TestAdminSender(AdminTestCase):
    
    model_admin_class = None # TODO: add 'SenderAdmin'
    model = sender
    exclude_expected = []
    fields_expected = []
    
    def test_get_search_fields(self):
        self.assertTrue('sender_alias__alias' in self.model_admin.get_search_fields())
    
class TestAdminSpielort(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = SpielortAdmin
    model = spielort
    fields_expected = ['name', 'ort']
        
class TestAdminVeranstaltung(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = VeranstaltungAdmin
    model = veranstaltung
    exclude_expected = ['genre', 'person', 'band']
    fields_expected = ['name', 'datum', 'spielort', 'ort']
        
class TestAdminProvenienz(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = ProvAdmin
    model = provenienz
    fields_expected = ['geber', 'typ']
    
    
    def test_has_adv_sf(self):
        self.assertFalse(self.model_admin.has_adv_sf())
        
    def test_lookup_allowed(self):
        # NOTE: Errr... this ALWAYS returns True
        self.assertTrue(self.model_admin.lookup_allowed(key='BEEP BOOP', value=None))
#        self.assertFalse(self.model_admin.lookup_allowed(key='beep_boop', value=None))  
    
#class TestAdminLagerort(AdminTestMethodsMixin, AdminTestCase):
#    
#    model_admin_class = None
#    model = lagerort
#    
#class TestAdminFormat(AdminTestMethodsMixin, AdminTestCase):
#    
#    model_admin_class = None
#    model = Format
    
class TestAdminBuch(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = BuchAdmin
    model = buch
    exclude_expected = ['autor']
    fields_expected = ['titel', 'titel_orig', ('jahr', 'verlag'), ('jahr_orig', 'verlag_orig'), 
            'ausgabe', 'auflage', 'buch_serie', 'buch_band', 
            ('sprache', 'sprache_orig'), 'ubersetzer', ('EAN', 'ISBN'), 'LCCN'
        ]

    def test_group_fields(self):        
        # BuchAdmin flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
        expected = ['titel', 'titel_orig', ('jahr', 'verlag'), ('jahr_orig', 'verlag_orig'), 
            'ausgabe', 'auflage', 'buch_serie', 'buch_band', 
            ('sprache', 'sprache_orig'), 'ubersetzer', ('EAN', 'ISBN'), 'LCCN'
        ]
        request = self.get_request()
        fields = self.model_admin.get_fields(request)
        self.assertEqual(self.model_admin.group_fields(), expected)
        
    
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
