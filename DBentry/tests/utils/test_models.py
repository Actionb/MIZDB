from django.core import exceptions

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
        buch = _models.buch
        # model buch has the four kinds of relations:
        # FK from bestand to buch
        # FK from buch to verlag
        # ManyToMany auto created band <-> buch
        # ManyToMany intermediary musiker <-> buch
        rev_fk = _models.bestand._meta.get_field('buch').remote_field
        fk = buch._meta.get_field('schriftenreihe').remote_field
        m2m_inter = buch.musiker.rel
        m2m_auto = buch.band.rel

        rels = utils.get_model_relations(buch)
        self.assertIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(buch, reverse=False)
        self.assertNotIn(rev_fk, rels)
        self.assertIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(buch, forward=False)
        self.assertIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(buch, forward=False, reverse=False)
        self.assertNotIn(rev_fk, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

    def test_get_required_fields(self):
        def required_field_names(model):
            return [f.name for f in utils.get_required_fields(model)]
        self.assertEqual(required_field_names(_models.person), ['nachname'])
        self.assertEqual(required_field_names(_models.musiker), ['kuenstler_name'])
        self.assertEqual(required_field_names(_models.genre), ['genre'])
        self.assertEqual(required_field_names(_models.band), ['band_name'])
        self.assertEqual(required_field_names(_models.autor), [])
        self.assertEqual(required_field_names(_models.ausgabe), ['magazin'])
        self.assertEqual(required_field_names(_models.magazin), ['magazin_name'])
        self.assertEqual(required_field_names(_models.ort), ['land'])
        self.assertEqual(
            required_field_names(_models.artikel), ['schlagzeile', 'seite', 'ausgabe'])
        # _models.geber.name field is required but has a default:
        self.assertEqual(required_field_names(_models.geber), [])
        self.assertEqual(required_field_names(_models.bestand), ['lagerort'])

    def test_get_updateable_fields(self):
        obj = make(_models.artikel)
        self.assertEqual(
            utils.get_updateable_fields(obj),
            ['seitenumfang', 'zusammenfassung', 'beschreibung', 'bemerkungen']
        )

        obj.seitenumfang = 'f'
        obj.beschreibung = 'Beep'
        self.assertEqual(utils.get_updateable_fields(obj), ['zusammenfassung', 'bemerkungen'])
        obj.zusammenfassung = 'Boop'
        self.assertEqual(utils.get_updateable_fields(obj), ['bemerkungen'])

        obj = make(_models.ausgabe)
        self.assertEqual(
            utils.get_updateable_fields(obj),
            ['status', 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
        )
        obj.status = 2
        self.assertNotIn('status', utils.get_updateable_fields(obj))

    def test_get_reverse_field_path(self):
        # no related_query_name or related_name
        rel = _models.ausgabe._meta.get_field('artikel')
        self.assertEqual(utils.get_reverse_field_path(rel, 'seite'), 'artikel__seite')

        # related_name
        rel = _models.buch._meta.get_field('buchband').remote_field
        self.assertEqual(utils.get_reverse_field_path(rel, 'titel'), 'buch_set__titel')

    def test_get_fields_and_lookups(self):
        path = 'ausgabe__e_datum__year__gte'
        fields, lookups = utils.get_fields_and_lookups(_models.artikel, path)
        expected_fields = [
            _models.artikel._meta.get_field('ausgabe'),
            _models.ausgabe._meta.get_field('e_datum')
        ]
        expected_lookups = ['year', 'gte']
        self.assertEqual(fields, expected_fields)
        self.assertEqual(lookups, expected_lookups)

    def test_get_fields_and_lookups_invalid_lookup(self):
        # Assert that get_fields_and_lookups raises FieldError on
        # encountering an invalid lookup.
        with self.assertRaises(exceptions.FieldError):
            utils.get_fields_and_lookups(_models.artikel, 'schlagzeile__year')
        with self.assertRaises(exceptions.FieldError):
            # Kalendar's primary key is a OneToOne to BaseBrochure.
            utils.get_fields_and_lookups(_models.Kalendar, 'pk__iexact')

    def test_get_fields_and_lookups_fielddoesnotexist(self):
        # Assert that get_fields_and_lookups raises FieldDoesNotExist
        # if the first field is not a model field of the given model.
        with self.assertRaises(exceptions.FieldDoesNotExist):
            utils.get_fields_and_lookups(_models.artikel, 'foo__icontains')
