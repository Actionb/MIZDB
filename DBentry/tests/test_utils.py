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
    
    @classmethod
    def setUpTestData(cls):
        super(TestMergingAusgabe, cls).setUpTestData()
        cls.merge_record1.beschreibung = 'Test'
        cls.merge_record1.save()
            
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
        
    @expectedFailure
    def test_merge_records_with_no_records_deleted(self):
        # The merge_records were not deleted after the merge, which, technically, did not even happen
        utils.merge_records(self.original, self.qs.none(), expand_original = False, request=self.request)
        self.assertRestDeleted()
        
    @expectedFailure
    def test_merge_records_with_unexpected_change(self):
        # Original was expanded by an unexpected value
        utils.merge_records(self.original, self.qs, expand_original = False, request=self.request)
        self.qs.filter(pk=self.original.pk).update(beschreibung='This should not happen.')
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
        
class TestMergingPerson(MergingTestCase, BasicMergeTestMixin):
    model = person

class TestMergingVideoManual(MergingTestCase):
    
    model = video
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        cls.sender_original = sender.objects.create(name='Original-Sender')
        cls.sender_merger = sender.objects.create(name='Merger-Sender')
        cls.obj1 = video.objects.create(titel = 'Original', tracks = 3, laufzeit = '10:22:22', sender = cls.sender_original)
        cls.obj2 = video.objects.create(titel = 'Merger', tracks = 3, laufzeit = '10:22:22', sender = cls.sender_merger)
        
        cls.band_original = band.objects.create(band_name = 'Original-Band')
        cls.band_merger = band.objects.create(band_name = 'Merger-Band')
        
        cls.obj1.band.add(cls.band_original)
        cls.obj2.band.add(cls.band_merger)
        
        cls.musiker_original = musiker.objects.create(kuenstler_name = 'Original-Musiker')
        cls.musiker_merger = musiker.objects.create(kuenstler_name = 'Merger-Musiker')
        
        cls.obj1.musiker.through.objects.create(video = cls.obj1, musiker = cls.musiker_original)
        cls.obj2.musiker.through.objects.create(video = cls.obj2, musiker = cls.musiker_merger)
        
        cls.bestand_original = bestand.objects.create(video = cls.obj1, lagerort=lagerort.objects.create(ort = 'Original-Lagerort'))
        cls.bestand_merger = bestand.objects.create(video = cls.obj2, lagerort=lagerort.objects.create(ort = 'Merger-Lagerort'))
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super().setUpTestData()

    def test_merge_records_expand(self):
        # A merge with expanding the original's values
        new_original, update_data = utils.merge_records(self.original, self.qs, expand_original = True, request=self.request)
        self.assertEqual(self.obj1.sender, self.sender_original)
        self.assertIn(self.bestand_original, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger, self.obj1.bestand_set.all())
        self.assertIn(self.musiker_original, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger, self.obj1.musiker.all())
        self.assertIn(self.band_original, self.obj1.band.all())
        self.assertIn(self.band_merger, self.obj1.band.all())
        self.assertEqual(self.obj1.titel, 'Original')
        self.assertEqual(str(self.obj1.laufzeit), '10:22:22')
        self.assertEqual(self.obj1.tracks, 3)
    
class TestMergingVideo(MergingTestCase, BasicMergeTestMixin):
    
    model = video
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        cls.sender_original = sender.objects.create(name='Original-Sender')
        cls.sender_merger = sender.objects.create(name='Merger-Sender')
        cls.obj1 = video.objects.create(titel = 'Original', tracks = 3, laufzeit = '10:22:22', sender = cls.sender_original)
        cls.obj2 = video.objects.create(titel = 'Merger', tracks = 4, laufzeit = '10:22:23', sender = cls.sender_merger)
        
        cls.band_original = band.objects.create(band_name = 'Original-Band')
        cls.band_merger = band.objects.create(band_name = 'Merger-Band')
        
        cls.obj1.band.add(cls.band_original)
        cls.obj2.band.add(cls.band_merger)
        
        cls.musiker_original = musiker.objects.create(kuenstler_name = 'Original-Musiker')
        cls.musiker_merger = musiker.objects.create(kuenstler_name = 'Merger-Musiker')
        
        cls.obj1.musiker.through.objects.create(video = cls.obj1, musiker = cls.musiker_original)
        cls.obj2.musiker.through.objects.create(video = cls.obj2, musiker = cls.musiker_merger)
        
        cls.bestand_original = bestand.objects.create(video = cls.obj1, lagerort=lagerort.objects.create(ort = 'Original-Lagerort'))
        cls.bestand_merger = bestand.objects.create(video = cls.obj2, lagerort=lagerort.objects.create(ort = 'Merger-Lagerort'))
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super().setUpTestData()
        
        

##############################################################################################################
# concat_limit
##############################################################################################################
    
class TestConcatLimit(SimpleTestCase):
    
    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        self.assertEqual(utils.concat_limit([]), '')
        self.assertEqual(utils.concat_limit(t), '2020, 2021, 2024')
        self.assertEqual(utils.concat_limit(t, width = 1), '2020, [...]')
        self.assertEqual(utils.concat_limit(t, width = 1, z = 6), '002020, [...]')

##############################################################################################################
# get_obj_link & link_list
##############################################################################################################       
class TestUtilsLinks(TestDataMixin, RequestTestCase):
    
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
        expected = '{}: <a href="{}">{}</a>'.format('Band', url, force_text(self.obj1))
        self.assertEqual(link, expected)
        
        link = utils.get_obj_link(self.obj1, self.super_user, include_name=False)
        url = '/admin/DBentry/band/{}/change/'.format(self.obj1.pk)
        expected = '<a href="{}">{}</a>'.format(url, force_text(self.obj1))
        self.assertEqual(link, expected)
        
    def test_link_list(self):
        expected_url = 'href="/admin/DBentry/band/{}/change/"'
        expected_name = ">{}</a>"
        request = self.get_request()
        links = utils.link_list(request, self.test_data).split(", ")
        for c, obj in enumerate(self.test_data):
            self.assertIn(expected_url.format(obj.pk), links[c])
            self.assertIn(expected_name.format(str(obj)), links[c])

##############################################################################################################
# get_relations_between_models
##############################################################################################################    
class TestGetRelationsBetweenModels(SimpleTestCase):
    
    def test_many_to_one(self):
        from DBentry.models import ausgabe, magazin
        expected = (ausgabe._meta.get_field('magazin'), magazin._meta.get_field('ausgabe'))
        self.assertEqual((utils.get_relations_between_models(ausgabe, magazin)), expected)
        self.assertEqual((utils.get_relations_between_models(magazin, ausgabe)), expected)
        self.assertEqual((utils.get_relations_between_models('ausgabe', 'magazin')), expected)
        self.assertEqual((utils.get_relations_between_models('magazin', 'ausgabe')), expected)
    
    def test_many_to_many(self):
        from DBentry.models import Format, FormatTag
        expected = (Format._meta.get_field('tag'), FormatTag._meta.get_field('format'))
        self.assertEqual((utils.get_relations_between_models(Format, FormatTag)), expected)
        self.assertEqual((utils.get_relations_between_models(FormatTag, Format)), expected)
        self.assertEqual((utils.get_relations_between_models('Format', 'FormatTag')), expected)
        self.assertEqual((utils.get_relations_between_models('FormatTag', 'Format')), expected)
