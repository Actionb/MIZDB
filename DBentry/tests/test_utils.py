from .base import *
from .data import *

from DBentry import utils

class BasicMergeTestMixin(object):
    #TODO:
    # test behaviour when merge cannot be completed due to an internal exception
    # test genre,schlagwort for self relations

    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        
    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertOriginalExpanded(expand_original = False)
        self.assertRelatedChanges()
        self.assertRestDeleted()

class TestMergingAusgabe(MergingTestCase): 
    
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        super(TestMergingAusgabe, cls).setUpTestData()
        cls.merge_record1.info = 'Test'
        cls.merge_record1.save()
            
    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertOriginalExpanded()
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertEqual(new_original.info, self.merge_record1.info)
        
    def test_merge_records_no_expand(self):
        # A merge without expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertOriginalExpanded(expand_original = False)
        self.assertRelatedChanges()
        self.assertRestDeleted()
        self.assertNotEqual(new_original.info, self.merge_record1.info)
        
    @expectedFailure
    def test_merge_records_with_no_records_deleted(self):
        # The merge_records were not deleted after the merge, which, technically, did not even happen
        utils.merge_records(self.original, self.qs.none(), expand_original = False, request=self.request)
        self.assertRestDeleted()
        
    @expectedFailure
    def test_merge_records_with_unexpected_change(self):
        # Original was expanded by an unexpected value
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.qs.filter(pk=self.original.pk).update(info='This should not happen.')
        self.assertOriginalExpanded(expand_original = False)
        
    @expectedFailure
    def test_merge_records_with_missing_relation_change(self):
        # Less related changes than expected
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.original.ausgabe_num_set.clear()
        self.assertRelatedChanges()
        
    @expectedFailure
    def test_merge_records_with_additional_relation_change(self):
        # More related changes than expected
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        new_num = ausgabe_num.objects.create(num=42)
        self.original.ausgabe_num_set.add(new_num)
        self.assertRelatedChanges()
        
    #@skifIf(cls.no_bestand)
    def test_merge_records_bestand_integrity(self):
        # Check that all bestände are accounted for in the new_original
        all_bestand = list(self.original.bestand_set.all()) + list(chain(*[list(merge_record.bestand_set.all()) for merge_record in self.merge_records]))
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertEqual(new_original.bestand_set.count(), len(all_bestand))
        for bestand_item in all_bestand:
            if not bestand_item in new_original.bestand_set.all():
                raise AssertionError('Bestand {} not found in new original.'.format(str(bestand_item)))
                
class TestMergingOrt(MergingTestCase, BasicMergeTestMixin):
    model = ort
    
class TestMergingArtikel(MergingTestCase, BasicMergeTestMixin):
    model = artikel
    
class TestMergingBand(MergingTestCase, BasicMergeTestMixin):
    model = band

class TestMergingMusiker(MergingTestCase, BasicMergeTestMixin):
    model = musiker
    
class TestMergingAudio(MergingTestCase, BasicMergeTestMixin):
    model = audio
    
class TestMergingAutor(MergingTestCase, BasicMergeTestMixin):
    model = autor
    
class TestMergingGenre(MergingTestCase, BasicMergeTestMixin):
    model = genre
    
class TestMergingSchlagwort(MergingTestCase, BasicMergeTestMixin):
    model = schlagwort
    
class TestMergingMagazin(MergingTestCase, BasicMergeTestMixin):
    model = magazin
    
class TestMergingPerson(MergingTestCase, BasicMergeTestMixin):
    model = person
    
class TestConcatLimit(SimpleTestCase):
    
    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        self.assertEqual(utils.concat_limit([]), '')
        self.assertEqual(utils.concat_limit(t), '2020, 2021, 2024')
        self.assertEqual(utils.concat_limit(t, width = 1), '2020, [...]')
        self.assertEqual(utils.concat_limit(t, width = 1, z = 6), '002020, [...]')
        
    
    
        
