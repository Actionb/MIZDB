from itertools import chain

from . import MergingTestCase
from DBentry import utils, models as _models
from DBentry.factory import make

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
        cls.band_original = obj1.band.get() # get() will complain if there's more than one record
        cls.musiker_original = obj1.musiker.get()
        cls.bestand_original = obj1.bestand_set.get()
        cls.obj1 = obj1
        
        obj2 = make(cls.model, 
            titel = 'Merger1', tracks = 3, band__extra = 1, musiker__extra = 1, bestand__extra = 1, 
        )
        cls.band_merger1 = obj2.band.get()
        cls.musiker_merger1 = obj2.musiker.get()
        cls.bestand_merger1 = obj2.bestand_set.get()
        cls.obj2 = obj2
        
        obj3 = make(cls.model, 
            titel = 'Merger2', tracks = 3, band__extra = 1, musiker__extra = 1, bestand__extra = 1,
            beschreibung = 'Hello!'
        )
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
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.tracks, 3)
        self.assertEqual(new_original.beschreibung, 'Hello!')
        
    def test_merge_records_no_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.assertEqual(new_original, self.obj1)
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
    
