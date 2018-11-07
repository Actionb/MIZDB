from .base import *

from DBentry.admin import *
from DBentry.sites import MIZAdminSite
from DBentry.changelist import *
          
class AdminTestMethodsMixin(object):
    
    crosslinks_relations = None
    crosslinks_labels = {}
    exclude_expected = None
    fields_expected = None
        
    def get_crosslinks(self, obj, labels=None):
        url =  '/admin/DBentry/{model_name}/?{fld_name}=' + str(obj.pk)
        links = self.model_admin.add_crosslinks(object_id=obj.pk, labels=labels).get('crosslinks')
        return links, url
        
    def assertCrosslinks(self, obj, expected):
        links, url_template = self.get_crosslinks(obj)
        for item in expected:
            x = {'url':url_template.format(model_name=item['model_name'], fld_name=item['fld_name']), 'label':item['label']}
            self.assertIn(x, links)
            links.remove(x)
        self.assertFalse(links)      
        
    def test_get_exclude(self):
        expected = self.exclude_expected or []
        self.assertEqual(self.model_admin.get_exclude(None), expected)
        
    def test_get_fields(self):
        expected = self.fields_expected or []
        self.assertEqual(self.model_admin.get_fields(self.get_request()), expected)
        
    def test_get_fieldsets(self):
        # Test that commentary fields are put into their own little fieldset, unless the ModelAdmin class specifies fieldsets
        fields = self.model_admin.get_fields(self.get_request())
        if not self.model_admin_class.fieldsets and ('beschreibung' in fields or 'bemerkungen' in fields):
            fieldsets  = self.model_admin.get_fieldsets(self.get_request())
            self.assertIn('Beschreibung & Bemerkungen', [fieldset[0] for fieldset in fieldsets])
            
    def test_formfield_for_foreignkey(self):
        # Test that every ForeignKey formfield gets a fancy select2 widget
        from DBentry.ac.widgets import MIZModelSelect2
        for fkey_field in get_model_fields(self.model, base = False, foreign = True, m2m = False):
            formfield = self.model_admin.formfield_for_foreignkey(fkey_field, self.get_request())
            self.assertIsInstance(formfield.widget, MIZModelSelect2, msg=fkey_field.name)
        
    def test_get_changelist(self):
        self.assertEqual(self.model_admin.get_changelist(self.get_request()), MIZChangeList)
    
    def test_get_search_fields(self):
        # search fields are largely declared with the models, the admin classes only add the exact =id lookup
        self.assertIn('=id', self.model_admin.get_search_fields())
        self.model_admin.search_fields = ['id']
        self.assertIn('=id', self.model_admin.get_search_fields())
        self.assertNotIn('id', self.model_admin.get_search_fields())
    
    def test_get_search_fields_extra_pk(self):
        # An extra 'pk' search field was added, it should be replaced by an '=id' lookup
        self.model_admin.search_fields = ['pk']
        self.assertEqual(self.model_admin.get_search_fields(), ['=id'])
        
    def test_media_prop(self):
        media = self.model_admin.media
        if self.model_admin.googlebtns:
            self.assertIn('admin/js/utils.js', media._js)
            
class TestMIZModelAdmin(AdminTestCase):
    
    model_admin_class = DateiAdmin
    model = datei
    test_data_count = 1
    
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
        self.assertIn('delete_selected', actions.keys())
        
        # superuser has all permissions inherently
        actions = self.model_admin.get_actions(self.get_request())
        self.assertEqual(len(actions), 2)   
        self.assertIn('delete_selected', actions.keys())
        self.assertIn('merge_records', actions.keys())
        
        # permission is a callable
        def perm(i, request):
            return request.user == self.noperms_user
        def action(model_admin, request, queryset):
            pass
        action.perm_required = [perm]
        
        self.model_admin.actions.append(action)
        actions = self.model_admin.get_actions(self.get_request(user=self.noperms_user))
        self.assertIn('action', actions.keys())
        
        actions = self.model_admin.get_actions(self.get_request(user=self.staff_user))
        self.assertNotIn('action', actions.keys())
        
        
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
        self.assertFalse('crosslinks' in response.context, msg='no crosslinks allowed in add views')
        
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
        
        # assert that the method can handle bad strings
        request = self.get_request(data={'_changelist_filters':'thisisbad'})
        with self.assertNotRaises(ValueError):
            cf_init_data = self.model_admin.get_changeform_initial_data(request)
            
    def test_construct_m2m_change_message(self):
        # auto created
        obj = datei.band.through.objects.create(
            band = band.objects.create(band_name='Testband'), 
            datei = self.obj1
        )
        expected = {'name': 'Band', 'object': 'Testband'}
        self.assertEqual(self.model_admin._construct_m2m_change_message(obj), expected)
        
        # not auto created
        obj = datei.musiker.through.objects.create(
            musiker = musiker.objects.create(kuenstler_name = 'Testmusiker'), 
            datei = self.obj1
        )
        expected = {'name': 'Musiker', 'object': 'Testmusiker'}
        self.assertEqual(self.model_admin._construct_m2m_change_message(obj), expected)
        
    def test_save_model(self):
        # save_model should not update the _name of a ComputedNameModel object
        obj = make(person, vorname = 'Alice', nachname = 'Testman')
        obj.nachname = 'Mantest'
        self.model_admin.save_model(None, obj, None, None)
        self.assertEqual(list(person.objects.filter(pk=obj.pk).values_list('_name', flat=True)), ['Alice Testman'])
        
    def test_save_related(self):
        # save_related should for an update of the _name of a ComputedNameModel object
        obj = make(person, vorname = 'Alice', nachname = 'Testman')
        obj.nachname = 'Mantest'
        obj.save(update=False)
        fake_form = type('Dummy', (object, ), {'instance':obj, 'save_m2m':lambda x=None:None})
        self.model_admin.save_related(None, fake_form, [], None)
        self.assertEqual(fake_form.instance._name, 'Alice Mantest')
        self.assertEqual(list(person.objects.filter(pk=obj.pk).values_list('_name', flat=True)), ['Alice Mantest'])
    
    def test_get_preserved_filters(self):
        query_string = '_changelist_filters=sender%3D1'
        path = self.add_path + '?_changelist_filters=sender=1'
        request_data = {'_changelist_filters': ['sender=1']}
        
        # Ignore requests without POST or or without _changelist_filters in GET
        request = self.get_request(path = self.add_path)
        filters = self.model_admin.get_preserved_filters(request)
        self.assertEqual(filters, '', msg = 'preserved_filters updated without request.POST and without _changelist_filters in request.GET')
        
        request = self.get_request(path = path)
        filters = self.model_admin.get_preserved_filters(request)
        self.assertEqual(filters, query_string, msg = 'preserved_filters updated without request.POST')
        
        request = self.get_request(path = self.add_path)
        request.POST = {'sender':'2'}
        filters = self.model_admin.get_preserved_filters(request)
        self.assertEqual(filters, '', msg = 'preserved_filters updated without _changelist_filters')
        
        # Do not use key value pairs from POST data that are not present in GET _changelist_filters 
        request = self.get_request(path = path, data = request_data)
        request.POST = {'titel':'Beep boop'}
        filters = self.model_admin.get_preserved_filters(request)
        self.assertEqual(filters, query_string, msg = 'preserved_filters updated for field not present in _changelist_filters')
        
        # Update the changelist filters if applicable
        request = self.get_request(path = path, data = request_data)
        request.POST = {'sender':'2'}
        filters = self.model_admin.get_preserved_filters(request)
        self.assertEqual(filters, '_changelist_filters=sender%3D2', msg = 'preserved_filters not updated')
        
class TestAdminArtikel(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    exclude_expected = ['genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
    fields_expected = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(magazin, magazin_name = 'Testmagazin')
        cls.obj1 = make(artikel, 
            ausgabe__magazin=cls.mag, seite=1, schlagzeile='Test!', schlagwort__schlagwort = ['Testschlagwort1', 'Testschlagwort2'], 
            musiker__kuenstler_name = 'Alice Tester', band__band_name = 'Testband'
        )
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
        
    def test_get_changeform_initial_data_with_changelist_filters(self):
        # ArtikelAdmin.get_changeform_initial_data makes sure 'magazin' is in initial for the form
        # from ausgabe__magazin path
        initial = {'_changelist_filters':'ausgabe__magazin=326&q=asdasd&thisisbad'}
        request = self.get_request(data=initial)
        cf_init_data = self.model_admin.get_changeform_initial_data(request)
        self.assertEqual(cf_init_data.get('ausgabe__magazin'), '326')
        
    def test_add_crosslinks(self):
        obj = make(artikel, 
            musiker__extra = 1, spielort__extra = 1, schlagwort__extra = 1, ort__extra = 1, person__extra = 1, 
            autor__extra = 1, genre__extra = 1, veranstaltung__extra = 1, band__extra = 1
        )
        self.assertCrosslinks(obj, [])

class TestAdminAusgabe(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    exclude_expected = ['audio']
    fields_expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
   
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(ausgabe, 
            magazin__magazin_name = 'Testmagazin', ausgabe_jahr__jahr = [2020, 2021, 2022], ausgabe_num__num = [10, 11, 12], 
            ausgabe_lnum__lnum = [10, 11, 12], ausgabe_monat__monat__monat = ['Januar', 'Februar'], 
            artikel__schlagzeile = 'Test', artikel__seite = 1, bestand__lagerort__pk=[ZRAUM_ID, DUPLETTEN_ID], 
        )
        
        cls.test_data = [cls.obj1]
        
        super().setUpTestData()
        
    def test_get_changelist(self):
        self.assertEqual(self.model_admin.get_changelist(self.get_request()), AusgabeChangeList)
    
    def test_group_fields(self):        
        # AusgabenAdmin flds_to_group = [('status', 'sonderausgabe')]
        expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
        request = self.get_request()
        self.model_admin.get_fields(request)
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
        
    def test_zbestand(self):
        self.assertTrue(self.model_admin.zbestand(self.obj1))
        self.obj1.bestand_set.all().delete()
        self.assertFalse(self.model_admin.zbestand(self.obj1))
        
    def test_dbestand(self):
        self.assertTrue(self.model_admin.dbestand(self.obj1))
        self.obj1.bestand_set.all().delete()
        self.assertFalse(self.model_admin.dbestand(self.obj1))
        
    def test_add_crosslinks(self):
        obj = make(ausgabe, 
            ausgabe_num__extra = 1, ausgabe_lnum__extra = 1, ausgabe_monat__extra = 1, ausgabe_jahr__extra = 1, 
            artikel__extra = 1, audio__extra = 1, bestand__extra = 1, 
        )
        links, url = self.get_crosslinks(obj)
        self.assertEqual(len(links), 1)
        self.assertIn({'url':url.format(model_name='artikel', fld_name='ausgabe'), 'label': 'Artikel (1)'}, links)
        
        links, url = self.get_crosslinks(obj, labels={'artikel':'Beep boop'})
        self.assertIn({'url':url.format(model_name='artikel', fld_name='ausgabe'), 'label': 'Beep boop (1)'}, links)
        
        ausgabe.artikel_set.rel.related_name = 'Boop beep'
        links, url = self.get_crosslinks(obj)
        self.assertIn({'url':url.format(model_name='artikel', fld_name='ausgabe'), 'label': 'Boop Beep (1)'}, links)
        
        obj.artikel_set.all().delete()
        links, url = self.get_crosslinks(obj)
        self.assertFalse(links)
        
class TestAdminMagazin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = MagazinAdmin
    model = magazin
    exclude_expected = ['genre']
    fields_expected = ['magazin_name', 'erstausgabe', 'turnus', 'magazin_url', 'ausgaben_merkmal', 'fanzine', 'issn', 
        'beschreibung', 'bemerkungen', 'ort', 
    ]
    
    raw_data = [{'ausgabe__extra':1}]
        
    def test_anz_ausgaben(self):
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 1)
        ausgabe.objects.all().delete()
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 0)
        
    def test_add_crosslinks(self):
        obj = make(magazin, 
            ausgabe__extra = 1, autor__extra = 1, genre__extra = 1
        )
        expected = [
            {'model_name':'ausgabe', 'fld_name':'magazin', 'label': 'Ausgaben (1)'}, 
            {'model_name':'autor', 'fld_name':'magazin', 'label': 'Autoren (1)'} 
        ]
        self.assertCrosslinks(obj, expected)


class TestAdminPerson(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = PersonAdmin
    model = person
    exclude_expected = ['orte']
    fields_expected = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    
    raw_data = [
        {'musiker__extra':1, 'autor__extra':1},
        {}, 
    ]
    
    def test_Ist_Musiker(self):
        self.assertTrue(self.model_admin.Ist_Musiker(self.obj1))
        self.assertFalse(self.model_admin.Ist_Musiker(self.obj2))
        
    def test_Ist_Autor(self):
        self.assertTrue(self.model_admin.Ist_Autor(self.obj1))
        self.assertFalse(self.model_admin.Ist_Autor(self.obj2))
        
    def test_add_crosslinks(self):
        obj = make(person, 
            video__extra = 1, veranstaltung__extra = 1, herausgeber__extra = 1, datei__extra = 1, 
            artikel__extra = 1, orte__extra = 1, autor__extra = 1, memorabilien__extra = 1, musiker__extra = 1, 
            dokument__extra = 1, bildmaterial__extra = 1, technik__extra = 1, audio__extra = 1, buch__extra = 1,         
        )
        expected = [
            {'model_name':'video',          'fld_name':'person', 'label':'Video Materialien (1)'}, 
            {'model_name':'veranstaltung',  'fld_name':'person', 'label':'Veranstaltungen (1)'}, 
            {'model_name':'herausgeber',    'fld_name':'person', 'label':'Herausgeber (1)'}, 
            {'model_name':'datei',          'fld_name':'person', 'label':'Dateien (1)'}, 
            {'model_name':'artikel',        'fld_name':'person', 'label':'Artikel (1)'}, 
            {'model_name':'autor',          'fld_name':'person', 'label':'Autoren (1)'}, 
            {'model_name':'memorabilien',   'fld_name':'person', 'label':'Memorabilien (1)'}, 
            {'model_name':'dokument',       'fld_name':'person', 'label':'Dokumente (1)'}, 
            {'model_name':'bildmaterial',   'fld_name':'person', 'label':'Bild Materialien (1)'}, 
            {'model_name':'technik',        'fld_name':'person', 'label':'Technik (1)'}, 
            {'model_name':'audio',          'fld_name':'person', 'label':'Audio Materialien (1)'}, 
            {'model_name':'buch',           'fld_name':'person', 'label':'Bücher (1)'}, 
            {'model_name':'musiker',        'fld_name':'person', 'label':'Musiker (1)'}, 
        ]
        self.assertCrosslinks(obj, expected)
        
class TestAdminMusiker(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = MusikerAdmin
    model = musiker
    test_data_count = 1
    exclude_expected = ['genre', 'instrument', 'orte']
    fields_expected = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    
    raw_data = [
        {}, 
        {'band__band_name':['Testband1', 'Testband2'], 'genre__genre':['Testgenre1', 'Testgenre2']}
    ]
    
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
        o = make(ort, stadt='Dortmund', land__code = 'XYZ')
        self.obj2.orte.add(o)
        self.obj2.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj2), 'Dortmund, XYZ')
        
    def test_add_crosslinks(self):
        obj = make(musiker, 
            artikel__extra = 1, audio__extra = 1, band__extra = 1, bildmaterial__extra = 1, buch__extra = 1, 
            datei__extra = 1, dokument__extra = 1, memorabilien__extra = 1, instrument__extra = 1, orte__extra = 1, 
            genre__extra = 1, musiker_alias__extra = 1, technik__extra = 1, veranstaltung__extra = 1, video__extra = 1
        )
        expected = [
            {'model_name':'artikel',        'fld_name':'musiker', 'label':'Artikel (1)'}, 
            {'model_name':'audio',          'fld_name':'musiker', 'label':'Audio Materialien (1)'},
            {'model_name':'bildmaterial',   'fld_name':'musiker', 'label':'Bild Materialien (1)'},
            {'model_name':'buch',           'fld_name':'musiker', 'label':'Bücher (1)'}, 
            {'model_name':'datei',          'fld_name':'musiker', 'label':'Dateien (1)'}, 
            {'model_name':'dokument',       'fld_name':'musiker', 'label':'Dokumente (1)'},
            {'model_name':'memorabilien',   'fld_name':'musiker', 'label':'Memorabilien (1)'}, 
            {'model_name':'technik',        'fld_name':'musiker', 'label':'Technik (1)'},    
            {'model_name':'veranstaltung',  'fld_name':'musiker', 'label':'Veranstaltungen (1)'}, 
            {'model_name':'video',          'fld_name':'musiker', 'label':'Video Materialien (1)'},
        ]
        self.assertCrosslinks(obj, expected)
        
class TestAdminGenre(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = GenreAdmin
    model = genre
    test_data_count = 1
    fields_expected = ['genre', 'ober']
    
    raw_data = [
        {'genre':'Topobject'}, 
        {'genre':'Subobject', 'genre_alias__alias':['Alias1', 'Alias2'], 'ober__genre':'Topobject'}
    ]
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Alias1')
        self.assertIn(self.obj2, result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertIn(self.obj1, result)
        
    def test_search_for_top_not_finds_sub(self):
        # check if a search for a topobject does not find its subobjects
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Topobject')
        self.assertNotIn(self.obj2, result)
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj2), 'Alias1, Alias2')
        
    def test_ober_string(self):
        self.assertEqual(self.model_admin.ober_string(self.obj1), '')
        self.assertEqual(self.model_admin.ober_string(self.obj2), 'Topobject')
        
    def test_sub_string(self):
        self.assertEqual(self.model_admin.sub_string(self.obj1), 'Subobject')
        self.assertEqual(self.model_admin.sub_string(self.obj2), '')
    
    def test_get_search_fields(self):
        # genre/schlagwort admin removes the search field that results in all subobjects of a topobject
        # being present in a search for topobject.
        # This would be useful for dal, but not for searches on the changelist
        super().test_get_search_fields()
        self.assertNotIn('ober__genre', self.model_admin.get_search_fields())
        
    def test_add_crosslinks(self):
        obj = make(genre, 
            artikel__extra = 1, audio__extra = 1, band__extra = 1, bildmaterial__extra = 1, buch__extra = 1, 
            datei__extra = 1, dokument__extra = 1, sub_genres__extra = 1, genre_alias__extra = 1, magazin__extra = 1, 
            memorabilien__extra = 1, musiker__extra = 1, technik__extra = 1, veranstaltung__extra = 1, video__extra = 1, 
        )
        expected = [
            {'model_name':'artikel',        'fld_name':'genre', 'label':'Artikel (1)'}, 
            {'model_name':'audio',          'fld_name':'genre', 'label':'Audio Materialien (1)'}, 
            {'model_name':'band',           'fld_name':'genre', 'label':'Bands (1)'},
            {'model_name':'bildmaterial',   'fld_name':'genre', 'label':'Bild Materialien (1)'},
            {'model_name':'buch',           'fld_name':'genre', 'label':'Bücher (1)'}, 
            {'model_name':'datei',          'fld_name':'genre', 'label':'Dateien (1)'}, 
            {'model_name':'genre',          'fld_name':'ober',  'label':'Sub Genres (1)'}, 
            {'model_name':'magazin',        'fld_name':'genre', 'label':'Magazine (1)'}, 
            {'model_name':'dokument',       'fld_name':'genre', 'label':'Dokumente (1)'}, 
            {'model_name':'memorabilien',   'fld_name':'genre', 'label':'Memorabilien (1)'},
            {'model_name':'musiker',        'fld_name':'genre', 'label':'Musiker (1)'},
            {'model_name':'technik',        'fld_name':'genre', 'label':'Technik (1)'},    
            {'model_name':'veranstaltung',  'fld_name':'genre', 'label':'Veranstaltungen (1)'}, 
            {'model_name':'video',          'fld_name':'genre', 'label':'Video Materialien (1)'},
        ]
        self.assertCrosslinks(obj, expected)
    
class TestAdminSchlagwort(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = SchlagwortAdmin
    model = schlagwort
    fields_expected = ['schlagwort', 'ober']
    
    raw_data = [
        {'schlagwort':'Topobject'}, 
        {'schlagwort':'Subobject', 'schlagwort_alias__alias':['Alias1', 'Alias2'], 'ober__schlagwort':'Topobject'}
    ]
        
    def test_search_finds_alias(self):
        # check if an object can be found via its alias
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Alias1')
        self.assertIn(self.obj2, result)
        
    def test_search_for_sub_finds_top(self):
        # check if a search for a subobject finds its topobject
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Subobject')
        self.assertIn(self.obj1, result)
        
    def test_search_for_top_not_finds_sub(self):
        # check if a search for a topobject does not find its subobjects
        result, use_distinct = self.model_admin.get_search_results(request=None, queryset=self.queryset, search_term='Topobject')
        self.assertNotIn(self.obj2, result)
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj2), 'Alias1, Alias2')
        
    def test_ober_string(self):
        self.assertEqual(self.model_admin.ober_string(self.obj1), '')
        self.assertEqual(self.model_admin.ober_string(self.obj2), 'Topobject')
        
    def test_sub_string(self):
        self.assertEqual(self.model_admin.sub_string(self.obj1), 'Subobject')
        self.assertEqual(self.model_admin.sub_string(self.obj2), '')
    
    def test_get_search_fields(self):
        # genre/schlagwort admin removes the search field that results in all subobjects of a topobject
        # being present in a search for topobject.
        # This would be useful for dal, but not for searches on the changelist
        super().test_get_search_fields()
        self.assertNotIn('ober__schlagwort', self.model_admin.get_search_fields())
        
    def test_add_crosslinks(self):
        obj = make(schlagwort, 
            artikel__extra = 1, audio__extra = 1, bildmaterial__extra = 1, buch__extra = 1, 
            datei__extra = 1, dokument__extra = 1, unterbegriffe__extra = 1, schlagwort_alias__extra = 1, 
            memorabilien__extra = 1, technik__extra = 1, veranstaltung__extra = 1, video__extra = 1, 
        )
        expected = [
            {'model_name':'artikel',        'fld_name':'schlagwort', 'label':'Artikel (1)'}, 
            {'model_name':'audio',          'fld_name':'schlagwort', 'label':'Audio Materialien (1)'}, 
            {'model_name':'bildmaterial',   'fld_name':'schlagwort', 'label':'Bild Materialien (1)'},
            {'model_name':'buch',           'fld_name':'schlagwort', 'label':'Bücher (1)'}, 
            {'model_name':'datei',          'fld_name':'schlagwort', 'label':'Dateien (1)'}, 
            {'model_name':'schlagwort',     'fld_name':'ober',        'label':'Unterbegriffe (1)'}, 
            {'model_name':'dokument',       'fld_name':'schlagwort', 'label':'Dokumente (1)'}, 
            {'model_name':'memorabilien',   'fld_name':'schlagwort', 'label':'Memorabilien (1)'},
            {'model_name':'technik',        'fld_name':'schlagwort', 'label':'Technik (1)'},    
            {'model_name':'veranstaltung',  'fld_name':'schlagwort', 'label':'Veranstaltungen (1)'}, 
            {'model_name':'video',          'fld_name':'schlagwort', 'label':'Video Materialien (1)'},
        ]
        self.assertCrosslinks(obj, expected)
    
class TestAdminBand(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = BandAdmin
    model = band
    exclude_expected = ['genre', 'musiker', 'orte']
    fields_expected = ['band_name', 'beschreibung', 'bemerkungen']
    raw_data = [
        {
            'band_alias__alias':['Alias1', 'Alias2'], 'genre__genre':['Testgenre1', 'Testgenre2'],
            'musiker__kuenstler_name':['Testkuenstler1', 'Testkuenstler2']
        }
    ]
        
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
    raw_data = [
        {'magazin__magazin_name':['Testmagazin1', 'Testmagazin2']}
    ]
    
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
    
    def bland_forwarded(self):
        f = self.model_admin.get_form(self.get_request())
        self.assertEqual(f.base_fields['bland'].widget.widget.forward[0], ['land'])
            
        
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
    raw_data = [
        {'band__band_name':'Testband', 'musiker__kuenstler_name':'Alice Tester', 'format__format_typ__typ':['TestTyp1', 'TestTyp2']}
    ]

    def test_kuenstler_string(self):
        self.assertEqual(self.model_admin.kuenstler_string(self.obj1), 'Testband, Alice Tester')

    def test_formate_string(self):
        self.assertEqual(self.model_admin.formate_string(self.obj1), 'TestTyp1, TestTyp2')
        
    def test_add_crosslinks(self):
        obj = make(audio, 
            m2m_datei_quelle__extra = 1, ausgabe__extra = 1, genre__extra = 1, band__extra = 1, ort__extra = 1, 
            veranstaltung__extra = 1, bestand__extra = 1, schlagwort__extra = 1, format__extra = 1, spielort__extra = 1, 
            plattenfirma__extra = 1, musiker__extra = 1, person__extra = 1
        )
        links, url = self.get_crosslinks(obj)
        self.assertFalse(links, msg = 'Audio cannot have any crosslinks.')
    
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
    exclude_expected = [
        'herausgeber', 'autor', 'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung'
    ]
    fields_expected = [
            'titel', 'titel_orig', 'seitenumfang', 'jahr', 'jahr_orig', 'auflage', 'EAN', 'ISBN', 
            'is_buchband', 'beschreibung', 'bemerkungen', 'schriftenreihe', 'buchband', 'verlag', 'sprache', 
        ]
    
    @classmethod
    def setUpTestData(cls):
        p1 = make(person, vorname = 'Alice', nachname = 'Testman')
        p2 = make(person, vorname = 'Bob', nachname = 'Mantest')
        cls.obj1 = make(buch, 
            autor__person = [p1, p2], herausgeber__person = [p1, p2],
            schlagwort__schlagwort = ['Testschlagwort1', 'Testschlagwort2'], 
            genre__genre = ['Testgenre1', 'Testgenre2']
        )
        cls.test_data = [cls.obj1]
        super().setUpTestData()
    
    def test_autoren_string(self):
        self.assertEqual(self.model_admin.autoren_string(self.obj1), 'Alice Testman (AT), Bob Mantest (BM)')
        
    def test_herausgeber_string(self):
        self.assertEqual(self.model_admin.herausgeber_string(self.obj1), 'Alice Testman, Bob Mantest')
        
    def test_schlagwort_string(self):
        self.assertEqual(self.model_admin.schlagwort_string(self.obj1), 'Testschlagwort1, Testschlagwort2')
        
    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj1), 'Testgenre1, Testgenre2')
        
class TestAdminBaseBrochure(AdminTestCase):
    model_admin_class = BaseBrochureAdmin
    model = Brochure
    
    @translation_override(language = None)
    def test_get_fieldsets(self):
        # Assert that an extra fieldset vor the ausgabe__magazin, ausgabe group was added
        fieldsets = self.model_admin.get_fieldsets(self.get_request())
        # Should have three fieldsets: the default 'none', a beschreibung & bemerkungen and the ausgabe & ausgabe__magazin one
        self.assertEqual(len(fieldsets), 3)
        self.assertEqual(fieldsets[1][0], 'Beilage von Ausgabe')
        fieldset_options = fieldsets[1][1]
        self.assertIn('fields', fieldset_options)
        self.assertEqual(fieldset_options['fields'], [('ausgabe__magazin', 'ausgabe')])
        self.assertIn('description', fieldset_options)
        self.assertEqual(fieldset_options['description'], 'Geben Sie die Ausgabe an, der dieses Objekt beilag.')
        
class TestAdminKatalog(AdminTestCase):
    model_admin_class = KatalogAdmin
    model = Katalog
    
    def test_get_fieldsets(self):
        # Assert that 'art' and 'zusammenfassung' are swapped correctly
        none_fieldset_options = self.model_admin.get_fieldsets(self.get_request())[0][1]
        self.assertIn('fields', none_fieldset_options)
        self.assertIn('art', none_fieldset_options['fields'])
        art_index = none_fieldset_options['fields'].index('art')
        self.assertIn('zusammenfassung', none_fieldset_options['fields'])
        z_index = none_fieldset_options['fields'].index('zusammenfassung')
        self.assertTrue(art_index < z_index)
        
class TestAdminSite(UserTestCase):
    
    def test_app_index(self):
        response = self.client.get('/admin/DBentry/')
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.app_index.__name__)
        
        response = self.client.get('/admin/')
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.index.__name__)
        
    def test_index_DBentry(self):
        request = self.client.get('/admin/').wsgi_request
        response = miz_site.index(request)
        app_list = response.context_data['app_list']
        
        # check if there are two 'categories' (fake apps) for app DBentry (app_list was extended by two new app_dicts)
        app_names = [d.get('name','') for d in app_list]
        self.assertTrue('Archivgut' in app_names)
        self.assertTrue('Stammdaten' in app_names)
        self.assertTrue('Sonstige' in app_names)
        
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
