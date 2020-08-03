from django.core import exceptions

from DBentry import models as _models
from DBentry.search import utils
from DBentry.tests.base import MyTestCase


class TestUtils(MyTestCase):

    def test_get_dbfield_from_path(self):
        func = utils.get_dbfield_from_path
        test_data = [
            (
                _models.ausgabe, 'ausgabe_monat__monat__monat__contains',
                (_models.monat._meta.get_field('monat'), ['contains'])
            ),
            (
                _models.ausgabe, 'e_datum__year__gte',
                (_models.ausgabe._meta.get_field('e_datum'), ['year', 'gte'])
            ),
            (
                _models.artikel, 'seite__gt',
                (_models.artikel._meta.get_field('seite'), ['gt'])
            )
        ]
        for model, path, expected in test_data:
            with self.subTest(path=path):
                self.assertEqual(func(model, path), expected)

    def test_get_dbfield_from_path_returns_concrete_field(self):
        # Assert that get_dbfield_from_path only returns concrete model fields.
        # ausgabe__artikel would return the reverse ManyToOneRel.
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.get_dbfield_from_path(_models.ausgabe, 'artikel')
        expected = "Reverse relations not supported."
        self.assertEqual(cm.exception.args[0], expected)

    def test_get_dbfield_from_path_raises_fielddoesnotexist_on_invalid_path(self):
        with self.assertRaises(exceptions.FieldDoesNotExist) as cm:
            utils.get_dbfield_from_path(_models.ausgabe, 'not__a__valid__path')
        expected = "ausgabe has no field named 'not'"
        self.assertEqual(cm.exception.args[0], expected)
