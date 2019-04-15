import re
from itertools import chain
from .base import AdminTestCase, UserTestCase

from django.utils.translation import override as translation_override

import DBentry.admin as _admin
from DBentry.sites import miz_site
import DBentry.models as _models

from DBentry.sites import MIZAdminSite
from DBentry.utils import get_model_fields
from DBentry.factory import make, modelfactory_factory
from DBentry.changelist import MIZChangeList, AusgabeChangeList
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.templatetags.asf_tag import advanced_search_form as advanced_search_form_tag

class AdminTestMethodsMixin(object):
    
    crosslinks_object = None # the model instance with which the add_crosslinks method is to be tested 
    crosslinks_object_data = None # the data used to create the crosslinks_object with (via make())
    crosslinks_labels = None # the labels that the model_admin_class creates the crosslinks with
    crosslinks_expected = [] # the data that is expected to be returned by add_crosslinks
    exclude_expected = None # fields to be excluded from the changeview form
    fields_expected = None # fields expected to be on the changeview form
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        if not cls.crosslinks_object:
            if cls.crosslinks_object_data:
                cls.crosslinks_object = make(cls.model, **cls.crosslinks_object_data)
            else:
                cls.crosslinks_object = modelfactory_factory(cls.model).full_relations()
        
    def get_crosslinks(self, obj, labels=None):
        # Return the crosslinks bit of the 'new_extra' context the model_admin would add.
        labels = labels or self.crosslinks_labels or self.model_admin.crosslink_labels or {}
        return self.model_admin.add_crosslinks(object_id=obj.pk, labels=labels).get('crosslinks')
        
    def _prepare_crosslink_data(self, data, obj = None):
        # Return a dict based off of 'data' similar in structure of those in the crosslinks.
        if obj is not None and 'pk' not in data:
            data['pk'] = str(obj.pk)
        if 'url' in data:
            url = data['url']
        else:
            url = '/admin/DBentry/{model_name}/?{fld_name}={pk}'.format(**data)
        return {'url':url, 'label': data['label']}
        
    def assertInCrosslinks(self, expected, links):
        # Assert that the data given in 'expected' is found in iterable 'links'.
        # Add an url entry to that data if necessary.
        if 'url' in expected:
            url = expected['url']
        else:
            url = '/admin/DBentry/{model_name}/?{fld_name}={pk}'.format(**expected)
        data = {'url':url, 'label': expected['label']}
        self.assertIn(data, links)
        return data
        
    def assertAllCrosslinks(self, obj, expected, links = None, labels = None):
        # A crosslink will link to a changelist page of the related model with the related field filtered to the related object at hand.
        # For any relation given in crosslinks_relations check the existence and correctness of the url & label provided by model_admin.add_crosslinks.
        # expected must be an iterable of dicts with the keys model_name, fld_name and label.
        if links is None:
            links = self.get_crosslinks(obj, labels)
        _links = links.copy() 
        
        # Check if any expected crosslinks are missing and remove found expected crosslinks from 'links'.
        links_missing = []
        for item in expected:
            data = self._prepare_crosslink_data(item, obj)
            try:
                self.assertInCrosslinks(data, links)
            except AssertionError:
                links_missing.append(data)
            else:
                links.remove(data)
        if links_missing:
            sorting_key = lambda data: data['url']
            fail_message = 'The following crosslinks were not found:\n'
            fail_message += '\n'.join(str(l) for l in sorted(links_missing, key = sorting_key))
            fail_message += '\nCrosslinks available:\n'
            fail_message += '\n'.join(str(l) for l in sorted(_links, key = sorting_key))
            self.fail(fail_message)    
        if links:
            # There are some crosslinks left that were not expected:
            # check for any links that should not be in crosslinks because their model is in inlines already
            inline_crosslinks = []
            inline_model_names = [inline.model._meta.model_name for inline in self.model_admin.inlines]
            for i, link in enumerate(links.copy()):
                model_name_regex = re.search(r'DBentry/(\w+)/', link['url'])
                if not model_name_regex:
                    continue
                model_name = model_name_regex.groups()[0]
                if model_name in inline_model_names:
                    inline_crosslinks.append((model_name, links.pop(i)))
            
            fail_message = ''
            if inline_crosslinks:
                fail_message = 'The following crosslinks were added despite their model being present in the inlines already:\n'
                fail_message += '\n'.join(str(i) for i in inline_crosslinks)
            if links:
                # If there are still links left, then the test was not supplied with the full expected data.
                if fail_message: 
                    fail_message += '~'*20
                fail_message = 'The following crosslinks were added but no test data was supplied or the inline is missing:\n'
                fail_message += '\n'.join(str(i) for i in links)
            if fail_message:
                self.fail(fail_message)
        
    def test_add_crosslinks(self):
        if self.crosslinks_object and self.crosslinks_expected is not None:
            self.assertAllCrosslinks(self.crosslinks_object, self.crosslinks_expected)
        else:
            warning = 'Poorly configured TestCase:'
            if not self.crosslinks_object:
                warning += ' No crosslinks_object supplied.'
            if self.crosslinks_expected is None:
                warning += ' No crosslinks_expected supplied.'
            self.warn(warning)
            
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
        # (or replace an existing pk_name search field with an exact lookup)
        pk_name = self.model._meta.pk.name
        _backup = self.model_admin.search_fields
        self.assertIn('=pk' , self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = []
        self.assertIn('=pk' , self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = [pk_name]
        self.assertIn('=pk', self.model_admin.get_search_fields())
        self.assertNotIn(pk_name, self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = ["=" + pk_name]
        self.assertIn('=pk', self.model_admin.get_search_fields())
        self.assertNotIn("=" + pk_name, self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = ["pk"]
        self.assertIn('=pk', self.model_admin.get_search_fields())
        self.assertNotIn("pk", self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = ["beep", pk_name, "baap", "pk", "boop", "=" + pk_name]
        self.assertIn('=pk', self.model_admin.get_search_fields())
        self.assertEqual(["beep", "=pk", "baap", "boop"], self.model_admin.get_search_fields())
        
        self.model_admin.search_fields = _backup
        
    def test_media_prop(self):
        media = self.model_admin.media
        if self.model_admin.googlebtns:
            self.assertIn('admin/js/utils.js', media._js)
    
    def test_lookup_allowed_adv_sf(self):
        # Assert that all fields and their lookups belonging to advanced search form are allowed
        request = self.get_request()
        advsf_dict = advanced_search_form_tag(self.get_changelist(request = request))['asf'] # advsf_dict = dict(selects=[{},...], gtelt=[], simple=[], ac_form=form)
        for lookup_group_name, lookup_groups in advsf_dict.items():
            if lookup_group_name in ('selects', 'simple'):
                lookups = [lookup_group['query_string'] for lookup_group in lookup_groups]
            elif lookup_group_name == 'gtelt':
                # gtelt contains two lookups, gte_query_string and lt_query_string, wrangle them into a flattened iterator
                lookups = chain.from_iterable((lookup_group['gte_query_string'], lookup_group['lt_query_string']) for lookup_group in lookup_groups)
            elif lookup_group_name == 'ac_form':
                lookups = lookup_groups.base_fields.keys()
            else:
                # Agh, just continue I am bad at computers
                continue
                
            for lookup in lookups:
                self.assertTrue(self.model_admin.lookup_allowed(lookup = lookup, value = None), msg = 'lookup not allowed: ' + lookup)
            
class TestMIZModelAdmin(AdminTestCase):
    
    model_admin_class = _admin.DateiAdmin
    model = _models.datei
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
        obj = self.model.band.through.objects.create(
            band = _models.band.objects.create(band_name='Testband'), 
            datei = self.obj1
        )
        expected = {'name': 'Band', 'object': 'Testband'}
        self.assertEqual(self.model_admin._construct_m2m_change_message(obj), expected)
        
        # not auto created
        obj = self.model.musiker.through.objects.create(
            musiker = _models.musiker.objects.create(kuenstler_name = 'Testmusiker'), 
            datei = self.obj1
        )
        expected = {'name': 'Musiker', 'object': 'Testmusiker'}
        self.assertEqual(self.model_admin._construct_m2m_change_message(obj), expected)
        
    def test_save_model(self):
        # save_model should not update the _name of a ComputedNameModel object
        obj = make(_models.person, vorname = 'Alice', nachname = 'Testman')
        obj.nachname = 'Mantest'
        self.model_admin.save_model(None, obj, None, None)
        self.assertEqual(list(_models.person.objects.filter(pk=obj.pk).values_list('_name', flat=True)), ['Alice Testman'])
        
    def test_save_related(self):
        # save_related should for an update of the _name of a ComputedNameModel object
        obj = make(_models.person, vorname = 'Alice', nachname = 'Testman')
        obj.nachname = 'Mantest'
        obj.save(update=False)
        fake_form = type('Dummy', (object, ), {'instance':obj, 'save_m2m':lambda x=None:None})
        self.model_admin.save_related(None, fake_form, [], None)
        self.assertEqual(fake_form.instance._name, 'Alice Mantest')
        self.assertEqual(list(_models.person.objects.filter(pk=obj.pk).values_list('_name', flat=True)), ['Alice Mantest'])
    
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
       
    def test_get_search_fields(self):
        # Assert that get_search_fields does not include a iexact lookup for primary keys that are a relation
        search_fields = _admin.KatalogAdmin(_models.Katalog, self.admin_site).get_search_fields()
        self.assertNotIn('=basebrochure_ptr', search_fields)
                
class TestArtikelAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.ArtikelAdmin
    model = _models.artikel
    exclude_expected = ['genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung']
    fields_expected = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.magazin, magazin_name = 'Testmagazin')
        cls.obj1 = make(_models.artikel, 
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

class TestAusgabenAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.AusgabenAdmin
    model = _models.ausgabe
    exclude_expected = ['audio']
    fields_expected = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
    crosslinks_expected = [{'model_name': 'artikel', 'fld_name': 'ausgabe', 'label': 'Artikel (1)'}]
   
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(_models.ausgabe, 
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
        _models.artikel.objects.all().delete()
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
        
    def test_add_crosslinks_custom(self):
        obj = make(_models.ausgabe, 
            ausgabe_num__extra = 1, ausgabe_lnum__extra = 1, ausgabe_monat__extra = 1, ausgabe_jahr__extra = 1, 
            artikel__extra = 1, audio__extra = 1, bestand__extra = 1, 
        )
        # Only artikel should show up in the crosslinks as audio is present in the inlines.
        links = self.get_crosslinks(obj)
        self.assertEqual(len(links), 1)
        expected = {'model_name': 'artikel', 'fld_name': 'ausgabe', 'label': 'Artikel (1)', 'pk': str(obj.pk)}
        self.assertInCrosslinks(expected, links)
        
        links = self.get_crosslinks(obj, labels={'artikel':'Beep boop'})
        expected = {'model_name': 'artikel', 'fld_name': 'ausgabe', 'label': 'Beep boop (1)', 'pk': str(obj.pk)}
        self.assertInCrosslinks(expected, links)
        
        _related_name = _models.ausgabe.artikel_set.rel.related_name 
        _models.ausgabe.artikel_set.rel.related_name = 'Boop beep' # dangerous operation, the change persists beyond the test!
        links = self.get_crosslinks(obj)
        expected = {'model_name': 'artikel', 'fld_name': 'ausgabe', 'label': 'Boop Beep (1)', 'pk': str(obj.pk)} #Note the capitalization of each starting letter!
        self.assertInCrosslinks(expected, links)
        _models.ausgabe.artikel_set.rel.related_name = _related_name
        
        obj.artikel_set.all().delete()
        self.assertFalse(self.get_crosslinks(obj))
        
class TestMagazinAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.MagazinAdmin
    model = _models.magazin
    exclude_expected = ['genre', 'verlag', 'herausgeber']
    fields_expected = ['magazin_name', 'erstausgabe', 'turnus', 'magazin_url', 'ausgaben_merkmal', 'fanzine', 'issn', 
        'beschreibung', 'bemerkungen', 'ort', 
    ]

    crosslinks_expected = [
        {'model_name':'ausgabe', 'fld_name':'magazin', 'label': 'Ausgaben (1)'}, 
        {'model_name':'autor', 'fld_name':'magazin', 'label': 'Autoren (1)'} 
    ]
    
    raw_data = [{'ausgabe__extra':1}]
        
    def test_anz_ausgaben(self):
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 1)
        self.obj1.ausgabe_set.all().delete()
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.anz_ausgaben(self.obj1), 0)

class TestPersonAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.PersonAdmin
    model = _models.person
    exclude_expected = ['orte']
    fields_expected = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    test_data_count = 1 # one extra 'empty' object without relations for Ist_Autor/Ist_Musiker
    
    raw_data = [
        {'musiker__extra':1, 'autor__extra':1},
    ]
    
    crosslinks_expected = [
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
    
    def test_Ist_Musiker(self):
        self.assertTrue(self.model_admin.Ist_Musiker(self.obj1))
        self.assertFalse(self.model_admin.Ist_Musiker(self.obj2))
        
    def test_Ist_Autor(self):
        self.assertTrue(self.model_admin.Ist_Autor(self.obj1))
        self.assertFalse(self.model_admin.Ist_Autor(self.obj2))
        
    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj1), '')
        o = make(_models.ort, stadt='Dortmund', land__code = 'XYZ')
        self.obj1.orte.add(o)
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj1), 'Dortmund, XYZ')
        
class TestMusikerAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.MusikerAdmin
    model = _models.musiker
    test_data_count = 1
    exclude_expected = ['genre', 'instrument', 'orte']
    fields_expected = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    
    raw_data = [
        {}, 
        {'band__band_name':['Testband1', 'Testband2'], 'genre__genre':['Testgenre1', 'Testgenre2']}
    ]
    
    crosslinks_expected = [
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
        
    def test_add_extra_context(self):
        extra = self.model_admin.add_extra_context(object_id=self.obj1.pk)
        self.assertTrue('crosslinks' in extra)
        
    def test_band_string(self):
        self.assertEqual(self.model_admin.band_string(self.obj2), 'Testband1, Testband2')
        
    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj2), 'Testgenre1, Testgenre2')
        
    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj2), '')
        o = make(_models.ort, stadt='Dortmund', land__code = 'XYZ')
        self.obj2.orte.add(o)
        self.obj2.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj2), 'Dortmund, XYZ')
        
class TestGenreAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.GenreAdmin
    model = _models.genre
    test_data_count = 1
    fields_expected = ['genre', 'ober']
    
    raw_data = [
        {'genre':'Topobject'}, 
        {'genre':'Subobject', 'genre_alias__alias':['Alias1', 'Alias2'], 'ober__genre':'Topobject'}
    ]
    
    crosslinks_expected = [
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
    
class TestSchlagwortAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.SchlagwortAdmin
    model = _models.schlagwort
    fields_expected = ['schlagwort', 'ober']
    
    raw_data = [
        {'schlagwort':'Topobject'}, 
        {'schlagwort':'Subobject', 'schlagwort_alias__alias':['Alias1', 'Alias2'], 'ober__schlagwort':'Topobject'}
    ]
    
    crosslinks_expected = [
        {'model_name':'artikel',        'fld_name':'schlagwort', 'label':'Artikel (1)'}, 
        {'model_name':'audio',          'fld_name':'schlagwort', 'label':'Audio Materialien (1)'}, 
        {'model_name':'bildmaterial',   'fld_name':'schlagwort', 'label':'Bild Materialien (1)'},
        {'model_name':'brochure',       'fld_name':'schlagwort', 'label': 'Broschüren (1)'}, 
        {'model_name':'buch',           'fld_name':'schlagwort', 'label':'Bücher (1)'}, 
        {'model_name':'datei',          'fld_name':'schlagwort', 'label':'Dateien (1)'}, 
        {'model_name':'schlagwort',     'fld_name':'ober',        'label':'Unterbegriffe (1)'}, 
        {'model_name':'dokument',       'fld_name':'schlagwort', 'label':'Dokumente (1)'}, 
        {'model_name':'memorabilien',   'fld_name':'schlagwort', 'label':'Memorabilien (1)'},
        {'model_name':'technik',        'fld_name':'schlagwort', 'label':'Technik (1)'},    
        {'model_name':'veranstaltung',  'fld_name':'schlagwort', 'label':'Veranstaltungen (1)'}, 
        {'model_name':'video',          'fld_name':'schlagwort', 'label':'Video Materialien (1)'},
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
    
class TestBandAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.BandAdmin
    model = _models.band
    exclude_expected = ['genre', 'musiker', 'orte']
    fields_expected = ['band_name', 'beschreibung', 'bemerkungen']
    raw_data = [
        {
            'band_alias__alias':['Alias1', 'Alias2'], 'genre__genre':['Testgenre1', 'Testgenre2'],
            'musiker__kuenstler_name':['Testkuenstler1', 'Testkuenstler2']
        }
    ]
    
    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'band', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'band', 'label': 'Audio Materialien (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'band', 'label': 'Bild Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'band', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'band', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'band', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'band', 'label': 'Memorabilien (1)'},
        {'model_name': 'technik', 'fld_name': 'band', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'band', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'video', 'fld_name': 'band', 'label': 'Video Materialien (1)'},
    ]
        
    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj1), 'Alias1, Alias2')
        
    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj1), 'Testgenre1, Testgenre2')
        
    def test_musiker_string(self):
        self.assertEqual(self.model_admin.musiker_string(self.obj1), 'Testkuenstler1, Testkuenstler2')
    
    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj1), '')
        o = make(_models.ort, stadt='Dortmund', land__code = 'XYZ')
        self.obj1.orte.add(o)
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj1), 'Dortmund, XYZ')

class TestAutorAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.AutorAdmin
    model = _models.autor
    exclude_expected = ['magazin']
    fields_expected = ['kuerzel', 'beschreibung', 'bemerkungen', 'person']
    raw_data = [
        {'magazin__magazin_name':['Testmagazin1', 'Testmagazin2']}
    ]
    crosslinks_object_data = {'artikel__extra': 1, 'magazin__extra': 1, 'buch__extra': 1}
    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'autor', 'label': 'Artikel (1)'}, 
        {'model_name': 'buch', 'fld_name': 'autor', 'label': 'Bücher (1)'}, 
    ]
    
    def test_magazin_string(self):
        self.assertEqual(self.model_admin.magazin_string(self.obj1), 'Testmagazin1, Testmagazin2')
        
class TestOrtAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.OrtAdmin   
    model = _models.ort
    fields_expected = ['stadt', 'land', 'bland']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'ort', 'label': 'Artikel (1)'}, 
        {'model_name': 'audio', 'fld_name': 'ort', 'label': 'Audio Materialien (1)'}, 
        {'model_name': 'band', 'fld_name': 'orte', 'label': 'Bands (1)'},  
        {'model_name': 'bildmaterial', 'fld_name': 'ort', 'label': 'Bild Materialien (1)'}, 
        {'model_name': 'buch', 'fld_name': 'ort', 'label': 'Bücher (1)'}, 
        {'model_name': 'datei', 'fld_name': 'ort', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'ort', 'label': 'Dokumente (1)'}, 
        {'model_name': 'magazin', 'fld_name': 'ort', 'label': 'Magazine (1)'}, 
        {'model_name': 'memorabilien', 'fld_name': 'ort', 'label': 'Memorabilien (1)'}, 
        {'model_name': 'musiker', 'fld_name': 'orte', 'label': 'Musiker (1)'}, 
        {'model_name': 'person', 'fld_name': 'orte', 'label': 'Personen (1)'}, 
        {'model_name': 'spielort', 'fld_name': 'ort', 'label': 'Spielorte (1)'}, 
        {'model_name': 'technik', 'fld_name': 'ort', 'label': 'Technik (1)'}, 
        {'model_name': 'verlag', 'fld_name': 'sitz', 'label': 'Verlage (1)'}, 
    ]
    
    def bland_forwarded(self):
        f = self.model_admin.get_form(self.get_request())
        self.assertEqual(f.base_fields['bland'].widget.widget.forward[0], ['land'])
        
class TestLandAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.LandAdmin
    model = _models.land
    fields_expected = ['land_name', 'code']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'ort', 'fld_name': 'land', 'label': 'Orte (1)'}, 
        {'model_name': 'bundesland', 'fld_name': 'land', 'label': 'Bundesländer (1)'}
    ]
        
class TestBlandAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.BlandAdmin
    model = _models.bundesland
    fields_expected = ['bland_name', 'code', 'land']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'ort', 'fld_name': 'bland', 'label': 'Orte (1)'}, 
        {'model_name': 'kreis', 'fld_name': 'bland', 'label': 'Kreise (1)'}
    ]
        
class TestInstrumentAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.InstrumentAdmin
    model = _models.instrument
    fields_expected = ['instrument', 'kuerzel']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'musiker', 'fld_name': 'instrument', 'label': 'Musiker (1)'}
    ]
    
class TestAudioAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.AudioAdmin
    model = _models.audio
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
        
    
class TestSpielortAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.SpielortAdmin
    model = _models.spielort
    fields_expected = ['name', 'ort']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'dokument',      'fld_name': 'spielort', 'label': 'Dokumente (1)'}, 
        {'model_name': 'memorabilien',  'fld_name': 'spielort', 'label': 'Memorabilien (1)'}, 
        {'model_name': 'video',         'fld_name': 'spielort', 'label': 'Video Materialien (1)'}, 
        {'model_name': 'kalendar',      'fld_name': 'spielort', 'label': 'Programmhefte (1)'}, 
        {'model_name': 'buch',          'fld_name': 'spielort', 'label': 'Bücher (1)'}, 
        {'model_name': 'bildmaterial',  'fld_name': 'spielort', 'label': 'Bild Materialien (1)'}, 
        {'model_name': 'datei',         'fld_name': 'spielort', 'label': 'Dateien (1)'}, 
        {'model_name': 'artikel',       'fld_name': 'spielort', 'label': 'Artikel (1)'}, 
        {'model_name': 'audio',         'fld_name': 'spielort', 'label': 'Audio Materialien (1)'}, 
        {'model_name': 'technik',       'fld_name': 'spielort', 'label': 'Technik (1)'}, 
        {'model_name': 'veranstaltung', 'fld_name': 'spielort', 'label': 'Veranstaltungen (1)'}
    ]
        
class TestVeranstaltungAdmin(AdminTestMethodsMixin, AdminTestCase):
    
    model_admin_class = _admin.VeranstaltungAdmin
    model = _models.veranstaltung
    exclude_expected = ['genre', 'person', 'band', 'schlagwort', 'musiker']
    fields_expected = ['name', 'datum', 'spielort']
    test_data_count = 1
    
    crosslinks_expected = [
        {'model_name': 'technik',       'fld_name': 'veranstaltung', 'label': 'Technik (1)'}, 
        {'model_name': 'dokument',      'fld_name': 'veranstaltung', 'label': 'Dokumente (1)'}, 
        {'model_name': 'memorabilien',  'fld_name': 'veranstaltung', 'label': 'Memorabilien (1)'}, 
        {'model_name': 'video',         'fld_name': 'veranstaltung', 'label': 'Video Materialien (1)'}, 
        {'model_name': 'kalendar',      'fld_name': 'veranstaltung', 'label': 'Programmhefte (1)'}, 
        {'model_name': 'buch',          'fld_name': 'veranstaltung', 'label': 'Bücher (1)'}, 
        {'model_name': 'bildmaterial',  'fld_name': 'veranstaltung', 'label': 'Bild Materialien (1)'}, 
        {'model_name': 'datei',         'fld_name': 'veranstaltung', 'label': 'Dateien (1)'}, 
        {'model_name': 'artikel',       'fld_name': 'veranstaltung', 'label': 'Artikel (1)'}, 
        {'model_name': 'audio',         'fld_name': 'veranstaltung', 'label': 'Audio Materialien (1)'}
    ]
    
class TestVerlagAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VerlagAdmin
    model = _models.verlag
    fields_expected = ['verlag_name', 'sitz']
    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'verlag', 'label': 'Bücher (1)'}, 
        {'model_name': 'magazin', 'fld_name': 'verlag', 'label': 'Magazine (1)'}
    ]
    
class TestBuchAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BuchAdmin
    model = _models.buch
    exclude_expected = [
        'herausgeber', 'autor', 'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung'
    ]
    fields_expected = [
            'titel', 'titel_orig', 'seitenumfang', 'jahr', 'jahr_orig', 'auflage', 'EAN', 'ISBN', 
            'is_buchband', 'beschreibung', 'bemerkungen', 'schriftenreihe', 'buchband', 'verlag', 'sprache', 
        ]
    
    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'buchband', 'label': 'Einzelbänder (1)'}, 
    ]
    
    @classmethod
    def setUpTestData(cls):
        p1 = make(_models.person, vorname = 'Alice', nachname = 'Testman')
        p2 = make(_models.person, vorname = 'Bob', nachname = 'Mantest')
        cls.obj1 = make(cls.model, 
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
        
class BaseBrochureMixin(object):
    # BaseBrochure and its descendants use a OneToOneField as primary key which does not support the 
    # 'iexact' lookup that django's ModelAdmin.get_search_results.construct_search replaces the '=' with.
    # admin.get_search_fields thus does not add a primary key search field for BaseBrochure or its children.
    search_fields_expected = None
        
    def test_get_search_fields(self):
        if self.search_fields_expected is None:
            return
        self.assertEqual(self.model_admin.get_search_fields(), self.search_fields_expected)

class TestBaseBrochureAdmin(AdminTestCase):
    model_admin_class = _admin.BaseBrochureAdmin
    model = _models.Brochure
    
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
        
class TestBrochureAdmin(BaseBrochureMixin, AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BrochureAdmin
    model = _models.Brochure
    fields_expected = ['titel',  'zusammenfassung',  'bemerkungen',  'ausgabe',  'beschreibung',  'ausgabe__magazin']
    exclude_expected = ['genre', 'schlagwort']
    search_fields_expected = ['titel', 'zusammenfassung', 'bemerkungen', 'beschreibung']
        
class TestKatalogAdmin(BaseBrochureMixin, AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KatalogAdmin
    model = _models.Katalog
    fields_expected = ['titel',  'zusammenfassung',  'bemerkungen',  'ausgabe',  'beschreibung',  'art',  'ausgabe__magazin']
    exclude_expected = ['genre']
    search_fields_expected = ['titel', 'zusammenfassung', 'bemerkungen', 'beschreibung', 'art']
    
    def test_get_fieldsets(self):
        # Assert that 'art' and 'zusammenfassung' are swapped correctly
        none_fieldset_options = self.model_admin.get_fieldsets(self.get_request())[0][1]
        self.assertIn('fields', none_fieldset_options)
        self.assertIn('art', none_fieldset_options['fields'])
        art_index = none_fieldset_options['fields'].index('art')
        self.assertIn('zusammenfassung', none_fieldset_options['fields'])
        z_index = none_fieldset_options['fields'].index('zusammenfassung')
        self.assertTrue(art_index < z_index)
        
class TestKalendarAdmin(BaseBrochureMixin, AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KalendarAdmin
    model = _models.Kalendar
    fields_expected = ['titel',  'zusammenfassung',  'bemerkungen',  'ausgabe',  'beschreibung',  'ausgabe__magazin']
    exclude_expected = ['genre', 'spielort', 'veranstaltung']
    search_fields_expected = ['titel', 'zusammenfassung', 'bemerkungen', 'beschreibung']
        
class TestMemoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.MemoAdmin
    model = _models.memorabilien
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = ['genre',  'schlagwort',  'person',  'band',  'musiker',  'ort',  'spielort',  'veranstaltung']

class TestDokumentAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DokumentAdmin
    model = _models.dokument
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = ['genre',  'schlagwort',  'person',  'band',  'musiker',  'ort',  'spielort',  'veranstaltung']
    
class TestTechnikAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.TechnikAdmin
    model = _models.technik
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = ['genre',  'schlagwort',  'person',  'band',  'musiker',  'ort',  'spielort',  'veranstaltung']
    
class TestVideoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VideoAdmin
    model = _models.video
    fields_expected = ['titel',  'tracks',  'laufzeit',  'festplatte',  'quelle',  'beschreibung',  'bemerkungen',  'sender']
    exclude_expected = ['band',  'genre',  'musiker',  'person',  'schlagwort',  'spielort',  'veranstaltung']
    
class TestKreisAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KreisAdmin
    model = _models.kreis
    fields_expected = ['name', 'bland']
    
class TestBestandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BestandAdmin
    model = _models.bestand
    fields_expected = [
        'bestand_art',  'lagerort',  'provenienz',  'audio',  'ausgabe',  'bildmaterial',  
        'brochure',  'buch',  'dokument',  'memorabilien',  'technik',  'video'
    ]
    
class TestDateiAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DateiAdmin
    model = _models.datei
    fields_expected = ['titel',  'media_typ',  'datei_pfad',  'beschreibung',  'bemerkungen',  'quelle',  'sender',  'provenienz']
    exclude_expected = ['genre',  'schlagwort',  'person',  'band',  'musiker',  'ort',  'spielort',  'veranstaltung']
    
class TestHerausgeberAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.HerausgeberAdmin
    model = _models.Herausgeber
    fields_expected = ['person', 'organisation']
    
    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'herausgeber', 'label': 'Bücher (1)'}, 
        {'model_name': 'magazin', 'fld_name': 'herausgeber', 'label': 'Magazine (1)'}
    ]
    
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
        expected_model_admin = _admin.ArtikelAdmin
        self.assertIsInstance(miz_site.get_admin_model(_models.artikel), expected_model_admin)
        self.assertIsInstance(miz_site.get_admin_model('DBentry.artikel'), expected_model_admin)
        self.assertIsNone(miz_site.get_admin_model('BEEP.BOOP'))
