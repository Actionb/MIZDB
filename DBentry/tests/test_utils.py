import datetime
import re
from collections import OrderedDict
from itertools import chain

from .base import MyTestCase, RequestTestCase, MergingTestCase
from .mixins import TestDataMixin

from django.utils.encoding import force_text
from django.forms import Media

import DBentry.models as _models
from DBentry import utils
from DBentry.factory import make
from DBentry.sites import miz_site

from nameparser import HumanName

##############################################################################################################
# general utilities
############################################################################################################## 
class TestUtils(MyTestCase):
    
    def test_is_iterable(self):
        self.assertTrue(utils.is_iterable(list()))
        self.assertTrue(utils.is_iterable(tuple()))
        self.assertTrue(utils.is_iterable(dict()))
        self.assertTrue(utils.is_iterable(set()))
        self.assertTrue(utils.is_iterable(OrderedDict()))
        self.assertFalse(utils.is_iterable("abc"))
        
    def test_flatten_dict(self):
        d = {
            'dont_flatten' : 1, 
            'dont_flatten_str' : 'abc', 
            'dont_flatten_iterable' : [1, 2], 
            'flatten' : [3], 
            'excluded' : [4], 
            'recursive' : {
                'dont_flatten' : 1, 
                'flatten' : [2], 
                'excluded' : [4]
            }, 
        }
        
        flattened = utils.flatten_dict(d, exclude = ['excluded'])
        self.assertEqual(flattened['dont_flatten'], 1)
        self.assertEqual(flattened['dont_flatten_str'], 'abc')
        self.assertEqual(flattened['dont_flatten_iterable'], [1, 2])
        self.assertEqual(flattened['flatten'], 3)
        self.assertEqual(flattened['excluded'], [4])
        self.assertEqual(flattened['recursive']['dont_flatten'], 1)
        self.assertEqual(flattened['recursive']['flatten'], 2)
        self.assertEqual(flattened['recursive']['excluded'], [4])
  
  
##############################################################################################################
# model utilities
##############################################################################################################  
class TestModelUtils(MyTestCase):
    
    def test_get_relations_between_models_many_to_one(self):
        from DBentry.models import ausgabe, magazin
        expected = (ausgabe._meta.get_field('magazin'), magazin._meta.get_field('ausgabe'))
        self.assertEqual((utils.get_relations_between_models(ausgabe, magazin)), expected)
        self.assertEqual((utils.get_relations_between_models(magazin, ausgabe)), expected)
        self.assertEqual((utils.get_relations_between_models('ausgabe', 'magazin')), expected)
        self.assertEqual((utils.get_relations_between_models('magazin', 'ausgabe')), expected)
    
    def test_get_relations_between_models_many_to_many(self):
        from DBentry.models import Format, FormatTag
        expected = (Format._meta.get_field('tag'), FormatTag._meta.get_field('format'))
        self.assertEqual((utils.get_relations_between_models(Format, FormatTag)), expected)
        self.assertEqual((utils.get_relations_between_models(FormatTag, Format)), expected)
        self.assertEqual((utils.get_relations_between_models('Format', 'FormatTag')), expected)
        self.assertEqual((utils.get_relations_between_models('FormatTag', 'Format')), expected)
        
    def test_is_protected(self):
        art = make(_models.artikel)
        self.assertIsNotNone(utils.is_protected([art.ausgabe]))
        self.assertIsNone(utils.is_protected([art]))
        
    def test_get_model_from_string(self):
        self.assertEqual(_models.ausgabe, utils.get_model_from_string('ausgabe'))
        self.assertIsNone(utils.get_model_from_string('beep boop'))
    
    def test_get_model_relations(self):
        video = _models.video
        # model video has the four kinds of relations:
        # FK from bestand to video
        # FK from video to sender
        # ManyToMany auto created band <-> video
        # ManyToMany intermediary musiker <-> video
        rev_fk = _models.bestand._meta.get_field('video').remote_field
        fk = video._meta.get_field('sender').remote_field
        m2m_inter = video.musiker.rel
        m2m_auto = video.band.rel
        
        rels = utils.get_model_relations(video)
        self.assertIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = utils.get_model_relations(video, reverse = False)
        self.assertNotIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = utils.get_model_relations(video, forward = False)
        self.assertIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = utils.get_model_relations(video, forward = False, reverse = False)
        self.assertNotIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
    def test_get_required_fields(self):
        def required_field_names(model):
            return [f.name for f in utils.get_required_fields(model)]
        self.assertListEqualSorted(required_field_names(_models.person), ['nachname'])
        self.assertListEqualSorted(required_field_names(_models.musiker), ['kuenstler_name'])
        self.assertListEqualSorted(required_field_names(_models.genre), ['genre'])
        self.assertListEqualSorted(required_field_names(_models.band), ['band_name'])
        self.assertListEqualSorted(required_field_names(_models.autor), [])
        self.assertListEqualSorted(required_field_names(_models.ausgabe), ['magazin'])
        self.assertListEqualSorted(required_field_names(_models.magazin), ['magazin_name'])
        self.assertListEqualSorted(required_field_names(_models.ort), ['land'])
        self.assertListEqualSorted(required_field_names(_models.artikel), ['schlagzeile', 'seite', 'ausgabe'])
        self.assertListEqualSorted(required_field_names(_models.geber), []) # 'name' field is required but has a default
        self.assertListEqualSorted(required_field_names(_models.bestand), ['lagerort'])

    def test_get_updateable_fields(self):
        obj = make(_models.artikel)
        self.assertListEqualSorted(utils.get_updateable_fields(obj), ['seitenumfang', 'zusammenfassung', 'beschreibung', 'bemerkungen'])

        obj.seitenumfang = 'f'
        obj.beschreibung = 'Beep'
        self.assertListEqualSorted(utils.get_updateable_fields(obj), ['bemerkungen', 'zusammenfassung'])
        obj.zusammenfassung = 'Boop'
        self.assertListEqualSorted(utils.get_updateable_fields(obj), ['bemerkungen'])
        
        obj = make(_models.ausgabe)
        self.assertListEqualSorted(utils.get_updateable_fields(obj), ['status', 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen'])
        obj.status = 2
        self.assertNotIn('status', utils.get_updateable_fields(obj))
        
        self.assertIn('turnus', utils.get_updateable_fields(obj.magazin))
        obj.magazin.turnus = 't'
        self.assertNotIn('turnus', utils.get_updateable_fields(obj.magazin))
        
    def test_get_reverse_field_path(self):
        # no related_query_name or related_name
        rel = _models.ausgabe._meta.get_field('artikel')
        self.assertEqual(utils.get_reverse_field_path(rel, 'seite'), 'artikel__seite')
        
        # related_name
        rel = _models.genre._meta.get_field('ober').remote_field
        self.assertEqual(utils.get_reverse_field_path(rel, 'genre'), 'sub_genres__genre')
        
        

##############################################################################################################
# debug utilities
##############################################################################################################   
class TestDebugUtils(MyTestCase):
    
    def test_num_queries(self):
        def func():
            return list(_models.ausgabe.objects.all())
        self.assertEqual(utils.num_queries(func), 1)


##############################################################################################################
# text utilities
##############################################################################################################
class TestTextUtils(MyTestCase):
    
    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        self.assertEqual(utils.concat_limit([]), '')
        self.assertEqual(utils.concat_limit(t), '2020, 2021, 2024')
        self.assertEqual(utils.concat_limit(t, width = 1), '2020, [...]')
        self.assertEqual(utils.concat_limit(t, width = 1, z = 6), '002020, [...]')
        
    def test_parse_name(self):
        expected = ("Alice Jane", "Tester")
        self.assertEqual(utils.parse_name("Alice Jane Tester"), expected)
        self.assertEqual(utils.parse_name("Prof. Alice Jane Tester"), expected)
        self.assertEqual(utils.parse_name("Alice Jane (Beep) Tester"), expected)
        self.assertEqual(utils.parse_name("Tester, Alice Jane"), expected)
        
    def test_coerce_human_name(self):
        # full_name is neither str nor HumanName
        self.assertIsInstance(utils.coerce_human_name(13), HumanName)
        self.assertIsInstance(utils.coerce_human_name('13'), HumanName)
        self.assertIsInstance(utils.coerce_human_name(HumanName('13')), HumanName)
    
    def test_parse_cl_querystring(self):
        self.assertEqual(utils.parse_cl_querystring(''), {})
        self.assertEqual(utils.parse_cl_querystring('_changelist_filters='), {})
        
        query_string = '_changelist_filters=ausgabe__magazin%3D326%26ausgabe%3D14962'
        expected = {'ausgabe__magazin': ['326'], 'ausgabe': ['14962']}
        self.assertEqual(utils.parse_cl_querystring(query_string), expected)
        
        query_string = '_changelist_filters=genre%3D824%26genre%3D594'
        expected = {'genre': ['824', '594']}
        self.assertEqual(utils.parse_cl_querystring(query_string), expected)
        
        

##############################################################################################################
# admin utils
##############################################################################################################       
class TestAdminUtils(TestDataMixin, RequestTestCase):
    
    model = _models.band
    test_data_count = 3
    opts = model._meta
    
    def test_get_obj_link_noperms(self):
        # Users without change permission should not get an edit link
        link = utils.get_obj_link(self.obj1, self.noperms_user)
        self.assertEqual(link, "{}: {}".format(self.opts.verbose_name, force_text(self.obj1)))
    
    def test_get_obj_link_noreversematch(self):
        # If there is no reverse match, no link should be displayed
        # get_obj_link uses the site_name argument to get the app's namespace
        from django.urls import NoReverseMatch
        with self.assertNotRaises(NoReverseMatch):
            link = utils.get_obj_link(self.obj1, self.super_user, site_name='BEEP BOOP')
        self.assertEqual(link, "{}: {}".format(self.opts.verbose_name, force_text(self.obj1)))
    
    def test_get_obj_link(self):
        link = utils.get_obj_link(self.obj1, self.super_user)
        url = '/admin/DBentry/band/{}/change/'.format(self.obj1.pk)
        expected = 'Band: <a href="{}">{}</a>'.format(url, force_text(self.obj1))
        self.assertEqual(link, expected)
        
        link = utils.get_obj_link(self.obj1, self.super_user, include_name=False)
        url = '/admin/DBentry/band/{}/change/'.format(self.obj1.pk)
        expected = '<a href="{}">{}</a>'.format(url, force_text(self.obj1))
        self.assertEqual(link, expected)
    
    def test_link_list(self):
        request = self.get_request()
        links = utils.link_list(request, self.test_data)
        for i, (url, label) in enumerate(re.findall(r'<a href="(.*?)">(.*?)</a>', links)):
            self.assertEqual(url, '/admin/DBentry/band/{}/change/'.format(self.test_data[i].pk))
            self.assertEqual(label, str(self.test_data[i]))
            
    def test_get_model_admin_for_model(self):
        from DBentry.admin import ArtikelAdmin
        self.assertIsInstance(utils.get_model_admin_for_model('artikel'), ArtikelAdmin)
        self.assertIsInstance(utils.get_model_admin_for_model(_models.artikel), ArtikelAdmin)
        self.assertIsNone(utils.get_model_admin_for_model('beepboop'))
        
    def test_has_admin_permission(self):
        from DBentry.admin import ArtikelAdmin, BildmaterialAdmin
        request = self.get_request(user = self.noperms_user)
        model_admin = ArtikelAdmin(_models.artikel, miz_site)
        self.assertFalse(utils.has_admin_permission(request, model_admin), msg = "Should return False for a user with no permissions.")
        
        from django.contrib.auth.models import Permission
        perms = Permission.objects.filter(codename__in=('add_artikel', ))
        self.staff_user.user_permissions.set(perms)
        request = self.get_request(user = self.staff_user)
        model_admin = ArtikelAdmin(_models.artikel, miz_site)
        self.assertTrue(utils.has_admin_permission(request, model_admin), msg = "Should return True for a user with at least some permissions for that model admin.")
    
        request = self.get_request(user = self.staff_user)
        model_admin = BildmaterialAdmin(_models.bildmaterial, miz_site)
        self.assertFalse(utils.has_admin_permission(request, model_admin), msg = "Should return False for non-superusers on a superuser only model admin.")
        
        request = self.get_request(user = self.super_user)
        model_admin = BildmaterialAdmin(_models.bildmaterial, miz_site)
        self.assertTrue(utils.has_admin_permission(request, model_admin), msg = "Should return True for superuser on a superuser-only model admin.")
            
    def test_make_simple_link(self):
        # No popup
        expected = '<a href="/test/beep/" target="_blank">TestLink</a>'
        self.assertEqual(utils.make_simple_link(url = "/test/beep/", label = "TestLink", is_popup = False, as_listitem = False), expected)
        expected = '<li><a href="/test/beep/" target="_blank">TestLink</a></li>'
        self.assertEqual(utils.make_simple_link(url = "/test/beep/", label = "TestLink", is_popup = False, as_listitem = True), expected)
        
        # As popups
        expected = '<a href="/test/beep/?_popup=1" onclick="return popup(this)">TestLink</a>'
        self.assertEqual(utils.make_simple_link(url = "/test/beep/", label = "TestLink", is_popup = True, as_listitem = False), expected)
        expected = '<li><a href="/test/beep/?_popup=1" onclick="return popup(this)">TestLink</a></li>'
        self.assertEqual(utils.make_simple_link(url = "/test/beep/", label = "TestLink", is_popup = True, as_listitem = True), expected)

##############################################################################################################
# date utils
############################################################################################################## 
class TestDateUtils(MyTestCase):
    
    def test_leapdays(self):
        # start.year == end.year no leap year
        self.assertEqual(utils.leapdays(datetime.date(2001, 1, 1), datetime.date(2001, 12, 31)), 0)
        # start.year == end.year with leap year including leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2000, 12, 31)), 1)
        # start.year == end.year with leap year excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2000, 1, 2)), 0)
        self.assertEqual(utils.leapdays(datetime.date(2000, 11, 11), datetime.date(2000, 12, 31)), 0)
        
        # start > end, leapdays should swap them
        self.assertEqual(utils.leapdays(datetime.date(2000, 12, 31), datetime.date(2000, 1, 1)), 1)
        
        # start is leap year, end is not leap year
        # including leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2001, 1, 1)), 1)
        
        # excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 3, 1), datetime.date(2001, 3, 1)), 0)
        
        # start is not leap year, end is leap year
        # including leap day
        self.assertEqual(utils.leapdays(datetime.date(2003, 3, 1), datetime.date(2004, 3, 1)), 1)
        
        # excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2003, 1, 1), datetime.date(2004, 1, 1)), 0)
        
        # start and end are leap years
        # start includes leap day, end excludes it
        self.assertEqual(utils.leapdays(datetime.date(2000,1,1), datetime.date(2004,1,1)), 1)
        
        # start excludes leap day, end includes it
        self.assertEqual(utils.leapdays(datetime.date(2000,3,1), datetime.date(2004,3,1)), 1)
        
        # start and end includes leap days
        self.assertEqual(utils.leapdays(datetime.date(2000,1,1), datetime.date(2004,3,1)), 2)
        
        # start and end exclude leap days
        self.assertEqual(utils.leapdays(datetime.date(2000,3,1), datetime.date(2004,1,1)), 0)
        
    def test_build_date(self):
        self.assertEqual(utils.build_date([2000], [1], 31), datetime.date(2000, 1, 31))
        self.assertEqual(utils.build_date([2000], [1], None), datetime.date(2000, 1, 1))
        
        self.assertEqual(utils.build_date([2001, 2000], [12], None), datetime.date(2000, 12, 1))
        # If there's more than one month, build_date should set the day to the last day of the min month
        self.assertEqual(utils.build_date([None, 2000], [12, 2], None), datetime.date(2000, 2, 29))
        # If there's more than one month and more than one year, 
        # build_date should set the day to the last day of the max month
        self.assertEqual(utils.build_date([2001, 2000], [12, 1], None), datetime.date(2000, 12, 31))
        
        self.assertIsNone(utils.build_date([None], [None]))
        self.assertIsNotNone(utils.build_date(2000, 1))
        

##############################################################################################################
# merging
##############################################################################################################
#TODO: merge_record: most of the TestClasses for models are VERY basic
class MergeTestMethodsMixin(object):


    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertOriginalExpandedLogged()
        self.assertRelatedChangesLogged()
        self.assertRestDeletedLogged()
        
    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertOriginalExpanded(expand_original = False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertOriginalExpandedLogged()
        self.assertRelatedChangesLogged()
        self.assertRestDeletedLogged()
        
class TestMergingAusgabe(MergingTestCase): 
    
    model = _models.ausgabe
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        default = dict(ausgabe_jahr__extra = 1, ausgabe_num__extra = 1, ausgabe_lnum__extra = 1, ausgabe_monat__extra = 1, bestand__extra = 1)
        cls.obj1 = make(cls.model, **default)
        cls.obj2 = make(cls.model, beschreibung = 'Test', **default)
        cls.obj3 = make(cls.model, **default)
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super(TestMergingAusgabe, cls).setUpTestData()
            
    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertEqual(new_original.beschreibung, self.merge_record1.beschreibung)
        
    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertOriginalExpanded(expand_original = False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertNotEqual(new_original.beschreibung, self.merge_record1.beschreibung)
        
    def test_merge_records_bestand_integrity(self):
        # Check that all bestände are accounted for in the new_original
        all_bestand = list(self.original.bestand_set.all()) + list(chain(*[list(merge_record.bestand_set.all()) for merge_record in self.merge_records]))
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertEqual(new_original.bestand_set.count(), len(all_bestand))
        for bestand_item in all_bestand:
            if not bestand_item in new_original.bestand_set.all():
                raise AssertionError('Bestand {} not found in new original.'.format(str(bestand_item)))
                
# The following test methods are rather tests for the assertions in MergingTestCase  
    def test_merge_records_with_no_records_deleted(self):
        # The merge_records were not deleted after the merge, which, technically, did not even happen
        utils.merge_records(self.original, self.qs.none(), expand_original = False, request=self.request)
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRestDeleted()
        self.assertTrue(context_manager.exception.args[0].startswith('Merged records were not deleted:'))
    
    def test_merge_records_with_unexpected_change(self):
        # Original was expanded by an unexpected value
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.qs.filter(pk=self.original.pk).update(beschreibung='This should not happen.')
        with self.assertRaises(AssertionError) as context_manager:
            self.assertOriginalExpanded(expand_original = False)
        self.assertTrue(context_manager.exception.args[0].startswith('Unexpected change with expand_original'))
    
    def test_merge_records_with_missing_relation_change(self):
        # Less related changes than expected
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.original.ausgabe_num_set.all().delete()
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRelatedChanges()
        self.assertTrue(context_manager.exception.args[0].startswith('Relation-Change did not occur for related object'))
        
    def test_merge_records_with_additional_relation_change(self):
        # More related changes than expected
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        make(_models.ausgabe_num, num = 42, ausgabe = self.original)
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRelatedChanges()
        self.assertTrue(context_manager.exception.args[0].startswith('Unexpected additional 1 relation-changes occurred: '))
                
class TestMergingOrt(MergingTestCase, MergeTestMethodsMixin):
    model = _models.ort

class TestMergingArtikel(MergingTestCase, MergeTestMethodsMixin):
    model = _models.artikel
    
class TestMergingBand(MergingTestCase, MergeTestMethodsMixin):
    model = _models.band

class TestMergingMusiker(MergingTestCase, MergeTestMethodsMixin):
    model = _models.musiker
    
class TestMergingAudio(MergingTestCase, MergeTestMethodsMixin):
    model = _models.audio
    
class TestMergingAutor(MergingTestCase, MergeTestMethodsMixin):
    model = _models.autor
    
class TestMergingGenre(MergingTestCase, MergeTestMethodsMixin):
    model = _models.genre
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, genre='Original')
        cls.obj2 = make(cls.model, genre='Merger1', ober=cls.obj1)
        cls.obj3 = make(cls.model, genre='Merger2')
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()
    
class TestMergingSchlagwort(MergingTestCase, MergeTestMethodsMixin):
    model = _models.schlagwort
    
class TestMergingMagazin(MergingTestCase, MergeTestMethodsMixin):
    
    model = _models.magazin
    test_data_count = 0
    
    
    @classmethod
    def setUpTestData(cls):
        
        cls.obj1 = cls.model.objects.create(magazin_name = 'Original-Magazin')
        cls.obj2 = cls.model.objects.create(magazin_name = 'Merger1-Magazin')
        cls.obj3 = cls.model.objects.create(magazin_name = 'Merger2-Magazin')
        
        cls.genre_original = _models.genre.objects.create(genre = 'Original-Genre')
        cls.genre_merger1 = _models.genre.objects.create(genre = 'Merger1-Genre')
        cls.genre_merger2 = _models.genre.objects.create(genre = 'Merger2-Genre')
        
        cls.model.genre.through.objects.create(genre=cls.genre_original, magazin=cls.obj1)
        cls.model.genre.through.objects.create(genre=cls.genre_merger1, magazin=cls.obj2)
        cls.model.genre.through.objects.create(genre=cls.genre_merger2, magazin=cls.obj3)
        
        autor_instance = _models.autor.objects.create(kuerzel='Merger1-Autor')
        cls.model.autor_set.through.objects.create(autor = autor_instance, magazin = cls.obj2)
        
        cls.ausgabe_original = _models.ausgabe.objects.create(
            beschreibung = 'Original-Ausgabe', sonderausgabe = True, magazin = cls.obj1
        )
        cls.ausgabe_merger = _models.ausgabe.objects.create(
            beschreibung = 'Merger1-Ausgabe', sonderausgabe = True, magazin = cls.obj2
        )
    
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]

        super().setUpTestData()
        
        
class TestMergingPerson(MergingTestCase, MergeTestMethodsMixin):
    model = _models.person
        
class VideoMergingDataMixin(object):
    
    model = _models.video
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        obj1 = make(cls.model, 
            titel = 'Original', tracks = 3, band__extra = 1, musiker__extra = 1, bestand__extra = 1, 
        )
        cls.sender_original = obj1.sender
        cls.band_original = obj1.band.get() # get() will complain if there's more than one record
        cls.musiker_original = obj1.musiker.get()
        cls.bestand_original = obj1.bestand_set.get()
        cls.obj1 = obj1
        
        obj2 = make(cls.model, 
            titel = 'Merger1', tracks = 3, band__extra = 1, musiker__extra = 1, bestand__extra = 1, 
        )
        cls.sender_merger1 = obj2.sender
        cls.band_merger1 = obj2.band.get()
        cls.musiker_merger1 = obj2.musiker.get()
        cls.bestand_merger1 = obj2.bestand_set.get()
        cls.obj2 = obj2
        
        obj3 = make(cls.model, 
            titel = 'Merger2', tracks = 3, band__extra = 1, musiker__extra = 1, bestand__extra = 1,
            beschreibung = 'Hello!'
        )
        cls.sender_merger2 = obj3.sender
        cls.band_merger2 = obj3.band.get()
        cls.musiker_merger2 = obj3.musiker.get()
        cls.bestand_merger2 = obj3.bestand_set.get()
        cls.obj3 = obj3
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()

class TestMergingVideoManual(VideoMergingDataMixin, MergingTestCase):

    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertEqual(new_original, self.obj1)
        
        self.assertEqual(self.obj1.sender, self.sender_original)
        
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.tracks, 3)
        self.assertEqual(new_original.beschreibung, 'Hello!')
        
    def test_merge_records_no_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertEqual(new_original, self.obj1)
        
        self.assertEqual(self.obj1.sender, self.sender_original)
        
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.tracks, 3)
        self.assertNotEqual(new_original.beschreibung, 'Hello!')
        
    def test_related_changes(self):
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        
        self.assertIn(self.bestand_original, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger1, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger2, self.obj1.bestand_set.all())
        
        self.assertIn(self.musiker_original, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger1, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger2, self.obj1.musiker.all())
        
        self.assertIn(self.band_original, self.obj1.band.all())
        self.assertIn(self.band_merger1, self.obj1.band.all())
        self.assertIn(self.band_merger2, self.obj1.band.all())
    
    def test_rest_deleted(self):
        utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        
        self.assertNotIn(self.obj2, self.model.objects.all())
        self.assertNotIn(self.obj3, self.model.objects.all())
    
# Using the more complex MergeTestMethodsMixin
class TestMergingVideo(VideoMergingDataMixin, MergingTestCase, MergeTestMethodsMixin):
    enforce_uniqueness = False
    
class TestEnsureJQuery(MyTestCase):
    
    def setUp(self):
        super().setUp()
        from django.conf import settings
        self.jquery_base = 'admin/js/vendor/jquery/jquery%s.js' % ('' if settings.DEBUG else '.min')
        self.jquery_init = 'admin/js/jquery.init.js'         
        self.test_js = [
            ['beep', 'boop'], 
            ['beep', self.jquery_base, 'boop', self.jquery_init], 
            [self.jquery_init, self.jquery_base, 'beep', 'boop'], 
            ['beep', 'boop', self.jquery_init]
        ]
        self.expected = [self.jquery_base, self.jquery_init, 'beep', 'boop']
            
    def test_ensure_jquery_media_object(self):
        media = Media(js = [])
        self.assertIsInstance(utils.ensure_jquery(media), Media)
        self.assertEqual(utils.ensure_jquery(media)._js, [self.jquery_base, self.jquery_init],  msg = "ensure_jquery should add jquery to empty media")
        
        for js in self.test_js:
            media = Media(js = js)
            with self.subTest():
                self.assertEqual(utils.ensure_jquery(media)._js,  self.expected)
        
    def test_ensure_jquery_as_func_decorator(self):
        def get_func(media):
            return lambda *args: media
        func = get_func(Media(js = []))
        self.assertEqual(utils.ensure_jquery(func)(None)._js, [self.jquery_base, self.jquery_init])
        
        for js in self.test_js:
            func = get_func(Media(js = js))
            with self.subTest():
                self.assertEqual(utils.ensure_jquery(func)(None)._js,  self.expected)
        
    
    def test_ensure_jquery_as_property_decorator(self):
        def get_prop(_media):
            return property(lambda *args: _media)
        
        prop = get_prop(Media(js = []))
        self.assertEqual(utils.ensure_jquery(prop).fget(1)._js, [self.jquery_base, self.jquery_init])
        
        for js in self.test_js:
            prop = get_prop(Media(js = js))
            with self.subTest():
                self.assertEqual(utils.ensure_jquery(prop).fget(1)._js,  self.expected)
        
