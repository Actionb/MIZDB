
from ..base import MyTestCase

from django.contrib import admin
from django.core import exceptions

from DBentry import models as _models

from DBentry.search import utils

class TestFieldFromPath(MyTestCase):
    
    def test_raises_fielddoesnotexist_on_invalid_path(self):
        with self.assertRaises(exceptions.FieldDoesNotExist):
            utils.get_dbfield_from_path(_models.ausgabe, 'not__a__valid__path')
    
    def test_error_raised_on_invalid_lookup(self):
        # A FieldError should be raised if invalid lookups for the field are found.
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.get_dbfield_from_path(_models.ausgabe, 'artikel__schlagzeile__notavalidlookup')
        self.assertIn('notavalidlookup', cm.exception.args[0])
        with self.assertRaises(exceptions.FieldError) as cm:
            utils.get_dbfield_from_path(_models.ausgabe, 'artikel__nota__validlookup')
        self.assertIn('nota', cm.exception.args[0])
        self.assertIn(', validlookup', cm.exception.args[0])
        
    def test_returns_concrete_field(self):
        # Assert that get_dbfield_from_path only returns concrete model fields.
        # ausgabe__artikel would return the reverse ManyToOneRel.
        db_field, lookups = utils.get_dbfield_from_path(_models.ausgabe, 'artikel')
        self.assertTrue(db_field.concrete)
        
    def test(self):
        func = utils.get_dbfield_from_path
        test_data = [
            (_models.ausgabe, 'ausgabe_monat__monat__monat__contains', 
            (_models.monat._meta.get_field('monat'), ['contains'])), 
            (_models.ausgabe, 'e_datum__year__gte', 
            (_models.ausgabe._meta.get_field('e_datum'), ['year', 'gte']))
        ]
        for model, path, expected in test_data:
            with self.subTest():
                self.assertEqual(func(model, path), expected)
        
