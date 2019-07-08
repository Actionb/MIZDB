from DBentry import utils, models as _models
from DBentry.factory import make
from DBentry.tests.base import MyTestCase

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
        
