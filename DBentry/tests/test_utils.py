from .base import *
from .data import *

from DBentry import utils

##############################################################################################################
# general utilities
############################################################################################################## 
class TestUtils(TestCase):
    
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
class TestModelUtils(TestCase):
    
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
        art = make(artikel)
        self.assertIsNotNone(utils.is_protected([art.ausgabe]))
        self.assertIsNone(utils.is_protected([art]))
        
    def test_get_model_from_string(self):
        self.assertEqual(ausgabe, utils.get_model_from_string('ausgabe'))
        self.assertIsNone(utils.get_model_from_string('beep boop'))
    
    def test_get_model_relations(self):
        # model video has the four kinds of relations:
        # FK from bestand to video
        # FK from video to sender
        # ManyToMany auto created band <-> video
        # ManyToMany intermediary musiker <-> video
        model = video
        rev_fk = bestand._meta.get_field('video').remote_field
        fk = video._meta.get_field('sender').remote_field
        m2m_inter = video.musiker.rel
        m2m_auto = video.band.rel
        
        rels = get_model_relations(video)
        self.assertIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = get_model_relations(video, reverse = False)
        self.assertNotIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = get_model_relations(video, forward = False)
        self.assertIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)
        
        rels = get_model_relations(video, forward = False, reverse = False)
        self.assertNotIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

##############################################################################################################
# debug utilities
##############################################################################################################   
class TestDebugUtils(TestCase):
    
    def test_num_queries(self):
        def func():
            return list(ausgabe.objects.all())
        self.assertEqual(utils.num_queries(func), 1)
        self.assertEqual(utils.num_queries(), 0) #TODO: have num_queries return 0 when no func is given


##############################################################################################################
# text utilities
##############################################################################################################
class TestTextUtils(TestCase):
    
    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        self.assertEqual(utils.concat_limit([]), '')
        self.assertEqual(utils.concat_limit(t), '2020, 2021, 2024')
        self.assertEqual(utils.concat_limit(t, width = 1), '2020, [...]')
        self.assertEqual(utils.concat_limit(t, width = 1, z = 6), '002020, [...]')

##############################################################################################################
# admin utils
##############################################################################################################       
class TestAdminUtils(TestDataMixin, RequestTestCase):
    
    model = band
    test_data_count = 3
    opts = band._meta
    
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
            
##############################################################################################################
# merging
##############################################################################################################
class MergeTestMethodsMixin(object):
    #TODO:
    # test behaviour when merge cannot be completed due to an internal exception
    # test genre,schlagwort for self relations
    # fix the logging

    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
#        self.assertOriginalExpandedLogged()
#        self.assertRelatedChangesLogged()
#        self.assertRestDeletedLogged()
        
    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertOriginalExpanded(expand_original = False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
#        self.assertOriginalExpandedLogged()
#        self.assertRelatedChangesLogged()
#        self.assertRestDeletedLogged()

class TestMergingAusgabe(MergingTestCase): 
    
    model = ausgabe
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        default = dict(ausgabe_jahr__extra = 1, ausgabe_num__extra = 1, ausgabe_lnum__extra = 1, ausgabe_monat__extra = 1, bestand__extra = 1)
        cls.obj1 = make(ausgabe, **default)
        cls.obj2 = make(ausgabe, beschreibung = 'Test', **default)
        cls.obj3 = make(ausgabe, **default)
        
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
        make(ausgabe_num, num = 42, ausgabe = self.original)
        with self.assertRaises(AssertionError) as context_manager:
            self.assertRelatedChanges()
        self.assertTrue(context_manager.exception.args[0].startswith('Unexpected additional 1 relation-changes occurred: '))
                
class TestMergingOrt(MergingTestCase, MergeTestMethodsMixin):
    model = ort
    
class TestMergingArtikel(MergingTestCase, MergeTestMethodsMixin):
    model = artikel
    
class TestMergingBand(MergingTestCase, MergeTestMethodsMixin):
    model = band

class TestMergingMusiker(MergingTestCase, MergeTestMethodsMixin):
    model = musiker
    
class TestMergingAudio(MergingTestCase, MergeTestMethodsMixin):
    model = audio
    
class TestMergingAutor(MergingTestCase, MergeTestMethodsMixin):
    model = autor
    
class TestMergingGenre(MergingTestCase, MergeTestMethodsMixin):
    model = genre
    
class TestMergingSchlagwort(MergingTestCase, MergeTestMethodsMixin):
    model = schlagwort
    
class TestMergingMagazin(MergingTestCase, MergeTestMethodsMixin):
    
    model = magazin
    test_data_count = 0
    
    
    @classmethod
    def setUpTestData(cls):
        
        cls.obj1 = magazin.objects.create(magazin_name = 'Original-Magazin')
        cls.obj2 = magazin.objects.create(magazin_name = 'Merger1-Magazin')
        cls.obj3 = magazin.objects.create(magazin_name = 'Merger2-Magazin')
        
        
        cls.genre_original = genre.objects.create(genre = 'Original-Genre')
        cls.genre_merger1 = genre.objects.create(genre = 'Merger1-Genre')
        cls.genre_merger2 = genre.objects.create(genre = 'Merger2-Genre')
        
        magazin.genre.through.objects.create(genre=cls.genre_original, magazin=cls.obj1)
        magazin.genre.through.objects.create(genre=cls.genre_merger1, magazin=cls.obj2)
        magazin.genre.through.objects.create(genre=cls.genre_merger2, magazin=cls.obj3)
        
        autor.magazin.through.objects.create(
            autor=autor.objects.create(kuerzel='Merger1-Autor'), magazin = cls.obj2
        )
        
        cls.ausgabe_original = ausgabe.objects.create(
            beschreibung = 'Original-Ausgabe', sonderausgabe = True, magazin = cls.obj1
        )
        cls.ausgabe_merger = ausgabe.objects.create(
            beschreibung = 'Merger1-Ausgabe', sonderausgabe = True, magazin = cls.obj2
        )
    
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]

        super().setUpTestData()
        
        
class TestMergingPerson(MergingTestCase, MergeTestMethodsMixin):
    model = person
        
class VideoMergingDataMixin(object):
    
    model = video
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        obj1 = make(video, 
            titel = 'Original', tracks = 3, laufzeit = '10:22:22', band__extra = 1, musiker__extra = 1, bestand__extra = 1, 
        )
        cls.sender_original = obj1.sender
        cls.band_original = obj1.band.get() # get() will complain if there's more than one record
        cls.musiker_original = obj1.musiker.get()
        cls.bestand_original = obj1.bestand_set.get()
        cls.obj1 = obj1
        
        obj2 = make(video, 
            titel = 'Merger1', tracks = 3, laufzeit = '10:22:22', band__extra = 1, musiker__extra = 1, bestand__extra = 1, 
        )
        cls.sender_merger1 = obj2.sender
        cls.band_merger1 = obj2.band.get()
        cls.musiker_merger1 = obj2.musiker.get()
        cls.bestand_merger1 = obj2.bestand_set.get()
        cls.obj2 = obj2
        
        obj3 = make(video, 
            titel = 'Merger2', tracks = 3, laufzeit = '10:22:22', band__extra = 1, musiker__extra = 1, bestand__extra = 1,
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
        self.assertEqual(str(new_original.laufzeit), '10:22:22')
        self.assertEqual(new_original.tracks, 3)
        self.assertEqual(new_original.beschreibung, 'Hello!')
        
    def test_merge_records_no_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertEqual(new_original, self.obj1)
        
        self.assertEqual(self.obj1.sender, self.sender_original)
        
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(str(new_original.laufzeit), '10:22:22')
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
    pass
    
