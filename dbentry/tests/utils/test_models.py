from functools import partial
from io import StringIO
from unittest.mock import patch, Mock

from django.contrib import auth, contenttypes
from django.core import exceptions

from dbentry import utils, models as _models
from dbentry.factory import make
from dbentry.tests.base import MyTestCase


# noinspection PyUnresolvedReferences
class TestModelUtils(MyTestCase):

    def test_get_relations_between_models_many_to_one(self):
        expected = (
            _models.Ausgabe._meta.get_field('magazin'),
            _models.Magazin._meta.get_field('ausgabe')
        )
        self.assertEqual(
            (utils.get_relations_between_models(_models.Ausgabe, _models.Magazin)), expected)
        self.assertEqual(
            (utils.get_relations_between_models(_models.Magazin, _models.Ausgabe)), expected)
        self.assertEqual(
            (utils.get_relations_between_models('Ausgabe', 'magazin')), expected)
        self.assertEqual(
            (utils.get_relations_between_models('Magazin', 'Ausgabe')), expected)

    def test_get_relations_between_models_many_to_many(self):
        expected = (
            _models.Artikel._meta.get_field('genre'),
            _models.Genre._meta.get_field('artikel')
        )
        self.assertEqual(
            (utils.get_relations_between_models(_models.Artikel, _models.Genre)), expected)
        self.assertEqual(
            (utils.get_relations_between_models(_models.Genre, _models.Artikel)), expected)
        self.assertEqual((utils.get_relations_between_models('Artikel', 'Genre')), expected)
        self.assertEqual((utils.get_relations_between_models('Genre', 'Artikel')), expected)

    def test_is_protected(self):
        art = make(_models.Artikel)
        self.assertIsNotNone(utils.is_protected([art.ausgabe]))
        self.assertIsNone(utils.is_protected([art]))

    def test_get_model_from_string(self):
        self.assertEqual(_models.Ausgabe, utils.get_model_from_string('Ausgabe'))
        self.assertIsNone(utils.get_model_from_string('beep boop'))

    def test_get_model_relations(self):
        buch = _models.Buch
        # model buch has the four kinds of relations:
        # FK from bestand to buch
        # FK from buch to verlag
        # ManyToMany auto created band <-> buch
        # ManyToMany intermediary Musiker <-> buch
        rev_fk = _models.Bestand._meta.get_field('buch').remote_field
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

        self.assertEqual(required_field_names(_models.Person), ['nachname'])
        self.assertEqual(required_field_names(_models.Musiker), ['kuenstler_name'])
        self.assertEqual(required_field_names(_models.Genre), ['genre'])
        self.assertEqual(required_field_names(_models.Band), ['band_name'])
        self.assertEqual(required_field_names(_models.Autor), [])
        self.assertEqual(required_field_names(_models.Ausgabe), ['magazin'])
        self.assertEqual(required_field_names(_models.Magazin), ['magazin_name'])
        self.assertEqual(required_field_names(_models.Ort), ['land'])
        self.assertEqual(
            required_field_names(_models.Artikel), ['schlagzeile', 'seite', 'ausgabe'])
        # _models.Provenienz.typ field is required but has a default:
        self.assertEqual(required_field_names(_models.Provenienz), ['geber'])
        self.assertEqual(required_field_names(_models.Bestand), ['lagerort'])

    def test_get_updatable_fields(self):
        obj = make(_models.Artikel)
        self.assertEqual(
            utils.get_updatable_fields(obj),
            ['seitenumfang', 'zusammenfassung', 'beschreibung', 'bemerkungen']
        )

        obj.seitenumfang = 'f'
        obj.beschreibung = 'Beep'
        self.assertEqual(utils.get_updatable_fields(obj), ['zusammenfassung', 'bemerkungen'])
        obj.zusammenfassung = 'Boop'
        self.assertEqual(utils.get_updatable_fields(obj), ['bemerkungen'])

        obj = make(_models.Ausgabe)
        self.assertEqual(
            utils.get_updatable_fields(obj),
            ['status', 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
        )
        obj.status = 2
        self.assertNotIn('status', utils.get_updatable_fields(obj))

    def test_get_reverse_field_path(self):
        # no related_query_name or related_name
        rel = _models.Ausgabe._meta.get_field('artikel')
        self.assertEqual(utils.get_reverse_field_path(rel, 'seite'), 'artikel__seite')

        # related_name
        rel = _models.Buch._meta.get_field('buchband').remote_field
        self.assertEqual(utils.get_reverse_field_path(rel, 'titel'), 'buch_set__titel')

    def test_get_fields_and_lookups(self):
        path = 'ausgabe__e_datum__year__gte'
        fields, lookups = utils.get_fields_and_lookups(_models.Artikel, path)
        expected_fields = [
            _models.Artikel._meta.get_field('ausgabe'),
            _models.Ausgabe._meta.get_field('e_datum')
        ]
        expected_lookups = ['year', 'gte']
        self.assertEqual(fields, expected_fields)
        self.assertEqual(lookups, expected_lookups)

    def test_get_fields_and_lookups_invalid_lookup(self):
        # Assert that get_fields_and_lookups raises FieldError on
        # encountering an invalid lookup.
        with self.assertRaises(exceptions.FieldError):
            utils.get_fields_and_lookups(_models.Artikel, 'schlagzeile__year')
        with self.assertRaises(exceptions.FieldError):
            # Kalender's primary key is a OneToOne to BaseBrochure.
            utils.get_fields_and_lookups(_models.Kalender, 'pk__iexact')

    def test_get_fields_and_lookups_fielddoesnotexist(self):
        # Assert that get_fields_and_lookups raises FieldDoesNotExist
        # if the first field is not a model field of the given model.
        with self.assertRaises(exceptions.FieldDoesNotExist):
            utils.get_fields_and_lookups(_models.Artikel, 'foo__icontains')


# noinspection PyUnresolvedReferences
class TestCleanPerms(MyTestCase):

    def setUp(self):
        super().setUp()
        self.patcher = partial(patch.object, auth.models.Permission.objects, 'all')

    @patch('sys.stdout')
    def test_stream_argument(self, mocked_stdout):
        # Assert that clean_permissions uses the stream kwarg or defaults
        # to sys.stdout.
        p = auth.models.Permission.objects.first()
        p.codename += 'beep'  # make the codename invalid to prompt a message
        p.save()
        utils.clean_permissions(stream=None)
        self.assertTrue(mocked_stdout.write.called)
        p.codename += 'beep'
        p.save()
        stream = StringIO()
        utils.clean_permissions(stream=stream)
        self.assertTrue(stream.getvalue())

    def test_unknown_model(self):
        # Assert that a message is written to the stream if clean_permissions
        # encounters a content type with an unknown model.
        ct = contenttypes.models.ContentType.objects.first()
        ct.model = 'Not.AModel'
        ct.save()
        p = auth.models.Permission.objects.first()
        p.content_type = ct
        p.save()
        expected_message = (
            "ContentType of %s references unknown model: %s.%s\n"
            "Try running clean_contenttypes.\n" % (
                p.name, p.content_type.app_label, p.content_type.model)
        )
        stream = StringIO()
        with self.patcher(new=Mock(return_value=[p])):
            utils.clean_permissions(stream)
            self.assertEqual(stream.getvalue(), expected_message)

    def test_only_default_perms(self):
        # Assert that clean_permissions only checks the default permissions.
        p = auth.models.Permission.objects.first()
        p.codename = 'beep_boop'
        p.save()
        stream = StringIO()
        # 'p' with permission 'beep' should just be skipped:
        with self.patcher(new=Mock(return_value=[p])):
            utils.clean_permissions(stream)
            self.assertFalse(stream.getvalue())

    def test_no_update_needed(self):
        # Assert that clean_permissions only updates a permission's codename if
        # that codename differs from the one returned by
        # auth.get_permission_codename.
        p = auth.models.Permission.objects.get(codename='add_ausgabe')
        p.codename = 'add_actuallyincorrect'
        p.save()
        stream = StringIO()
        mocked_get_codename = Mock(return_value='add_actuallyincorrect')
        with patch.object(auth, 'get_permission_codename', new=mocked_get_codename):
            with self.patcher(new=Mock(return_value=[p])):
                utils.clean_permissions(stream)
                self.assertFalse(stream.getvalue())

    def test_duplicate_permissions(self):
        # Assert that clean_permissions deletes redundant permissions.
        p = auth.models.Permission.objects.get(codename='add_ausgabe')
        # Dupe the perm just with a different codename;
        # clean_permissions will correct the codename and make the new perm a
        # true duplicate.
        new = auth.models.Permission.objects.create(
            name=p.name, codename='add_beep', content_type=p.content_type)
        expected_message = (
            "Permission with codename '%s' already exists. "
            "Deleting permission with outdated codename: '%s'\n" % (
                'add_ausgabe', 'add_beep')
        )
        stream = StringIO()
        with self.patcher(new=Mock(return_value=[new])):
            utils.clean_permissions(stream)
            self.assertEqual(stream.getvalue(), expected_message)
            self.assertFalse(new.pk)
