from django.core import exceptions

from dbentry import models as _models
from dbentry.search import utils
from dbentry.tests.base import MyTestCase


# noinspection PyUnresolvedReferences
class TestUtils(MyTestCase):

    def test_get_dbfield_from_path(self):
        func = utils.get_dbfield_from_path
        test_data = [
            (
                _models.Ausgabe, 'ausgabemonat__monat__monat__contains',
                (_models.Monat._meta.get_field('monat'), ['contains'])
            ),
            (
                _models.Ausgabe, 'e_datum__year__gte',
                (_models.Ausgabe._meta.get_field('e_datum'), ['year', 'gte'])
            ),
            (
                _models.Artikel, 'seite__gt',
                (_models.Artikel._meta.get_field('seite'), ['gt'])
            )
        ]
        for model, path, expected in test_data:
            with self.subTest(path=path):
                self.assertEqual(func(model, path), expected)

    def test_get_dbfield_from_path_returns_concrete_field(self):
        # Assert that get_dbfield_from_path only returns concrete model fields.
        # ausgabe__artikel would return the reverse ManyToOneRel.
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.get_dbfield_from_path(_models.Ausgabe, 'artikel')
        expected = "Reverse relations not supported."
        self.assertEqual(cm.exception.args[0], expected)

    def test_get_dbfield_from_path_raises_fielddoesnotexist_on_invalid_path(self):
        with self.assertRaises(exceptions.FieldDoesNotExist) as cm:
            utils.get_dbfield_from_path(_models.Ausgabe, 'not__a__valid__path')
        expected = "Ausgabe has no field named 'not'"
        self.assertEqual(cm.exception.args[0], expected)
