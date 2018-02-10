from django.urls import resolve

from .base import *

from DBentry.admin import *
from DBentry.sites import MIZAdminSite

class TestModelBase(AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    test_data_count = 3
    
    def test_get_actions(self): #TODO:
        pass
    
    def test_has_adv_sf(self):
        self.assertTrue(self.model_admin.has_adv_sf())  
        
    def test_get_changelist(self):
        self.assertEqual(self.model_admin.get_changelist(self.get_request()), MIZChangeList)
    
    def test_get_form(self):
        # test if 'magazin' gets wrapped
        request = self.get_request(path=self.add_path)
        form = self.model_admin.get_form(request)
        
        from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

        self.assertIsInstance(form.declared_fields['magazin'].widget, RelatedFieldWidgetWrapper)
        
    def test_get_exclude(self):
        expected = ['genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
        self.assertEqual(self.model_admin.get_exclude(None), expected)
        
    def test_get_fields(self):
        expected = [('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'info']
        self.assertEqual(self.model_admin.get_fields(self.get_request()), expected)
        
    def test_group_fields(self):
        request = self.get_request()
        fields = self.model_admin.get_fields(request) # sets model_admin.fields
        self.model_admin.fields = None
        self.assertEqual(self.model_admin.group_fields(), None)
        
        # ArtikelAdmin flds_to_group = [('ausgabe','magazin', 1),('seite', 'seitenumfang'),]
        expected = [('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'info']
        self.model_admin.fields = fields
        self.assertEqual(self.model_admin.group_fields(), expected)
        
    
    def test_get_search_fields(self):
        expected = {'info', 'seitenumfang', 'zusammenfassung', 'seite', 'schlagzeile'}
        self.assertEqual(self.model_admin.get_search_fields(), expected)
    
    def test_add_crosslinks(self):
        # artikel can't actually have any crosslinks
        links = self.model_admin.add_crosslinks(1).get('crosslinks')
        self.assertEqual(len(links), 0)
        
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
        
    def test_merge_allowed(self):
        the_new_guy = DataFactory().create_obj(artikel, create_new = True)
        qs = self.model.objects.all()
        request = self.get_request()
        self.assertFalse(self.model_admin.merge_allowed(request, qs))
        expected_message = 'Die ausgewählten {} gehören zu unterschiedlichen {}{}.'.format('Artikel', 'Ausgaben', '')
        messages = [str(msg) for msg in get_messages(request)]
        self.assertTrue(expected_message in messages) 

class TestAdminAusgabe(AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    test_data_count = 2

    def test_get_search_fields(self):
        expected = ['magazin__magazin_name', 'status', 'e_datum', 
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr','ausgabe_monat__monat__monat']
        self.assertEqual(self.model_admin.get_search_fields(), expected)
        
    def test_merge_allowed(self):
        qs = self.model.objects.all()
        request = self.get_request()
        self.assertTrue(self.model_admin.merge_allowed(request, qs))
        
        self.obj2.magazin = magazin.objects.create(magazin_name='Nope')
        self.obj2.save()
        qs = self.model.objects.all()
        request = self.get_request()
        self.assertFalse(self.model_admin.merge_allowed(request, qs))
        expected_message = 'Die ausgewählten Ausgaben gehören zu unterschiedlichen Magazinen.'
        messages = [str(msg) for msg in get_messages(request)]
        self.assertTrue(expected_message in messages)
        

class TestAdminPerson(AdminTestCase):
    
    model_admin_class = PersonAdmin
    model = person
    test_data_count = 1
    
    def test_Ist_Musiker(self):
        self.assertFalse(self.model_admin.Ist_Musiker(self.obj1))
        m = musiker.objects.create(kuenstler_name='Beep', person=self.obj1)
        self.assertTrue(self.model_admin.Ist_Musiker(self.obj1))
        
    def test_Ist_Autor(self):
        # check DataFactory for person -- person Ist_Autor but NOT Ist_Musiker from the start?
        self.assertTrue(self.model_admin.Ist_Autor(self.obj1))
        self.obj1.autor_set.all().delete()
        self.assertFalse(self.model_admin.Ist_Autor(self.obj1))
        
class TestAdminMusiker(AdminTestCase):
    
    model_admin_class = MusikerAdmin
    model = musiker
    test_data_count = 1
    
    def test_get_search_fields(self):
        expected = ['kuenstler_name', 'musiker_alias__alias'] 
        self.assertEqual(self.model_admin.get_search_fields(), expected)
    
    def test_get_fields(self):
        expected = ['kuenstler_name', ('person', 'herkunft_string'), 'beschreibung']
        self.assertEqual(self.model_admin.get_fields(self.get_request()), expected)
        
    def test_add_crosslinks(self):
        links = self.model_admin.add_crosslinks(object_id=self.obj1.pk).get('crosslinks')
        self.assertEqual(len(links), 5)
    
    def test_media_prop(self):
        self.assertTrue('admin/js/utils.js' in self.model_admin.media._js)
        
    def test_add_extra_context(self):
        extra = self.model_admin.add_extra_context(object_id=self.obj1.pk)
        self.assertTrue('crosslinks' in extra)
        
class TestAdminGenre(AdminTestCase):
    
    model_admin_class = GenreAdmin
    model = genre
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = genre.objects.create(genre='Topobject')
        cls.obj2 = genre.objects.create(genre='Subobject', ober=cls.obj1)
        cls.obj2.genre_alias_set.create(alias='ASubobjectLias')
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super(TestAdminGenre, cls).setUpTestData()
        
    def test_get_search_fields(self):
        expected = sorted({'genre', 'obergenre__genre', 'genre_alias__alias'})
        self.assertEqual(sorted(self.model_admin.get_search_fields()), expected)
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='ASubobjectLias')
        self.assertTrue(self.obj2 in result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertTrue(self.obj1 in result)
        
    @skip("Functionality may be scrapped in the future.")
    def test_search_for_sub_alias_finds_top(self):
        # check if a search for a subobject's alias also finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='ASubobjectLias')
        self.assertTrue(self.obj1 in result)
        
    
class TestAdminSchlagwort(AdminTestCase):
    
    model_admin_class = SchlagwortAdmin
    model = schlagwort
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = schlagwort.objects.create(schlagwort='Topobject')
        cls.obj2 = schlagwort.objects.create(schlagwort='Subobject', ober=cls.obj1)
        cls.obj2.schlagwort_alias_set.create(alias='ASubobjectLias')
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super(TestAdminSchlagwort, cls).setUpTestData()
    
    def test_get_search_fields(self):
        expected = sorted({'schlagwort', 'oberschl__schlagwort', 'schlagwort_alias__alias'})
        self.assertEqual(sorted(self.model_admin.get_search_fields()), expected)
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='ASubobjectLias')
        self.assertTrue(self.obj2 in result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertTrue(self.obj1 in result)
    
    @skip("Functionality may be scrapped in the future.")
    def test_search_for_sub_alias_finds_top(self):
        # check if a search for a subobject's alias also finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='ASubobjectLias')
        self.assertTrue(self.obj1 in result)
    
class TestAdminBand(AdminTestCase):
    
    model_admin_class = BandAdmin
    model = band
    
    def test_get_exclude(self):
        expected = ['genre', 'musiker']
        self.assertEqual(self.model_admin.get_exclude(None), expected)
        
    def test_get_search_fields(self):
        self.assertTrue('band_alias__alias' in self.model_admin.get_search_fields())

class TestAdminAutor(AdminTestCase):
    
    model_admin_class = AutorAdmin
    model = autor
    
    def test_get_search_fields(self):
        expected = ['person__vorname', 'person__nachname', 'kuerzel']
        self.assertEqual(self.model_admin.get_search_fields(), expected)
        
class TestAdminOrt(AdminTestCase):
    
    model_admin_class = OrtAdmin   
    model = ort
    
    def test_get_search_fields(self):
        expected = ['stadt', 'land__land_name', 'bland__bland_name']
        self.assertEqual(self.model_admin.get_search_fields(), expected)
        
class TestAdminLand(AdminTestCase):
    
    model_admin_class = LandAdmin
    model = land
    
    #TODO: implement
    @expectedFailure
    def test_get_search_fields(self):
        expected = ['id', 'land_name', 'code'] 
        self.assertEqual(self.model_admin.get_search_fields(), expected)
        self.assertTrue('land_alias__alias' in self.model_admin.get_search_fields())
        
class TestAdminBundesland(AdminTestCase):
    
    model_admin_class = BlandAdmin
    model = bundesland
    
    def test_get_search_fields(self):
        expected = ['id', 'bland_name', 'code', 'land__land_name']
        self.assertEqual(self.model_admin.get_search_fields(), expected)
        
class TestAdminInstrument(AdminTestCase):
    
    model_admin_class = InstrumentAdmin
    model = instrument
    
    #TODO: implement
    @expectedFailure
    def test_get_search_fields(self):
        self.assertTrue('instrument_alias__alias' in self.model_admin.get_search_fields())
    
class TestAdminAudio(AdminTestCase):
    
    model_admin_class = AudioAdmin
    model = audio
    
@skip('SenderAdmin not yet implemented')
class TestAdminSender(AdminTestCase):
    
    model_admin_class = None # TODO: add 'SenderAdmin'
    model = sender
    
    def test_get_search_fields(self):
        self.assertTrue('sender_alias__alias' in self.model_admin.get_search_fields())
    
class TestAdminSpielort(AdminTestCase):
    
    model_admin_class = SpielortAdmin
    model = spielort
    
    #TODO: implement
    @expectedFailure
    def test_get_search_fields(self):
        self.assertTrue('spielort_alias__alias' in self.model_admin.get_search_fields())
        
class TestAdminVeranstaltung(AdminTestCase):
    
    model_admin_class = VeranstaltungAdmin
    model = veranstaltung
    
    #TODO: implement
    @expectedFailure
    def test_get_search_fields(self):
        self.assertTrue('veranstaltung_alias__alias' in self.model_admin.get_search_fields())
        
class TestAdminProvenienz(AdminTestCase):
    
    model_admin_class = ProvAdmin
    model = provenienz
    
    def test_has_adv_sf(self):
        self.assertFalse(self.model_admin.has_adv_sf())
        
    def test_lookup_allowed(self):
        # Errr... this ALWAYS returns True
        self.assertTrue(self.model_admin.lookup_allowed(key='BEEP BOOP', value=None))
#        self.assertFalse(self.model_admin.lookup_allowed(key='beep_boop', value=None))  
        
    def test_merge_allowed(self):
        self.assertEqual(self.model_admin.merge_allowed(None, None), True) # best test ever
        
    #TODO: search_fields
    
class TestAdminLagerort(AdminTestCase):
    
    model_admin_class = None
    model = lagerort
    
class TestAdminFormat(AdminTestCase):
    
    model_admin_class = None
    model = Format
    
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
    
#    @classmethod
#    def setUpTestData(cls):
#        super(TestChangeList, self).setUpTestData()
#        cls.test_data = DataFactory().create_data(artikel)

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
    
    @expectedFailure
    def test_init_pagevar(self):
        # show that MIZChangeList can handle the PAGE_VAR
        request = self.get_request(path=self.changelist_path, data={'p':['1']})
        with self.assertRaises(IncorrectLookupParameters):
            MIZChangeList(request, **self.init_data.copy())
    
    @expectedFailure
    def test_init_errorvar(self):
        # show that MIZChangeList can handle the ERROR_FLAG
        request = self.get_request(path=self.changelist_path, data={'e':['1']})
        with self.assertRaises(IncorrectLookupParameters):
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
