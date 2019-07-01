
from ..base import MyTestCase

from django.core import exceptions

from DBentry import models as _models
from DBentry.search import utils

class TestUtils(MyTestCase):
    
    def test_validate_lookups(self):
        # A FieldError should be raised if invalid lookups for the field are found.
        db_field = _models.ausgabe._meta.get_field('artikel').field
        with self.assertNotRaises(exceptions.FieldError):
            utils.validate_lookups(db_field, ['in'])
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.validate_lookups(db_field, ['in', 'nota', 'validlookup'])
        self.assertIn('nota', cm.exception.args[0])
        self.assertIn(', validlookup', cm.exception.args[0])
        
    def test_get_fields_and_lookups_from_path(self):
        func = utils.get_fields_and_lookups_from_path
        test_data = [
            (_models.ausgabe, 'ausgabe_monat__monat__monat__contains', ['contains']), 
            (_models.ausgabe, 'e_datum__year__gte', ['year', 'gte']), 
            (_models.artikel, 'seite__gt', ['gt']), 
            (_models.artikel, 'notafield__lookup', ['notafield', 'lookup'])
        ]
        for model, path, expected in test_data:
            with self.subTest(path = path):
                self.assertEqual(func(model, path)[1], expected)
                
    def test_get_dbfield_from_path(self):
        func = utils.get_dbfield_from_path
        test_data = [
            (_models.ausgabe, 'ausgabe_monat__monat__monat__contains', 
            (_models.monat._meta.get_field('monat'), ['contains'])), 
            (_models.ausgabe, 'e_datum__year__gte', 
            (_models.ausgabe._meta.get_field('e_datum'), ['year', 'gte'])), 
            (_models.artikel, 'seite__gt', 
            (_models.artikel._meta.get_field('seite'), ['gt']))
        ]
        for model, path, expected in test_data:
            with self.subTest(path = path):
                self.assertEqual(func(model, path), expected)
        
    def test_get_dbfield_from_path_returns_concrete_field(self):
        # Assert that get_dbfield_from_path only returns concrete model fields.
        # ausgabe__artikel would return the reverse ManyToOneRel.
        db_field, lookups = utils.get_dbfield_from_path(_models.ausgabe, 'artikel')
        self.assertTrue(db_field.concrete)
        
    def test_get_dbfield_from_path_raises_fielddoesnotexist_on_invalid_path(self):
        with self.assertRaises(exceptions.FieldDoesNotExist) as cm:
            utils.get_dbfield_from_path(_models.ausgabe, 'not__a__valid__path')
        expected = "ausgabe has no field named 'not__a__valid__path'"
        self.assertEqual(cm.exception.args[0], expected)
