from unittest import expectedFailure
from itertools import chain

from django.test import TestCase, Client
from django.contrib.auth.models import User

from DBentry.models import *
from .data import DataFactory

class TestCaseUserMixin(object):
    
    @classmethod
    def setUpTestUser(cls):
        cls.client = Client()
        cls.user = User.objects.create_superuser(username='testuser', email='testtest@test.test', password='test1234')
        
class SuperUserTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_superuser(username='testuser', email='testtest@test.test', password='test1234')
        
    def setUp(self):
        self.client.force_login(self.user)
        
class TestBase(TestCase):
    
    model = None
    creator = DataFactory()
    
    @classmethod
    def setUpTestData(cls):
        cls.test_data = cls.creator.create_data(cls.model)
        

class TestMergingBase(TestBase):
    
    @classmethod
    def setUpTestData(cls):
        super(TestMergingBase, cls).setUpTestData()
        cls.original = cls.test_data.pop(0)
        cls.merge_records = []
        for c, merge_record in enumerate(cls.test_data, 1):
            setattr(cls, 'merge_record' + str(c), merge_record)
            cls.merge_records.append(merge_record)
        
    def setUp(self):
        self.original.refresh_from_db()
        for merge_record in self.merge_records:
            merge_record.refresh_from_db()
        self.ids = [self.original.pk] + [merge_record.pk for merge_record in self.merge_records]
        self.qs = self.model.objects.filter(pk__in=self.ids)
        
        # These are the related objects (as val_dicts) that are affected by the merge and should end up being related to original
        self.related_imprints = {}
        for rel in self.model._meta.related_objects:
            related_model = rel.field.model
            val_list = self.qs.values_list(rel.field.target_field.name) # Also include original's related objects!
            update_qs = related_model.objects.filter(**{ rel.field.name + '__in' : val_list })
            
            # These are the fields that *should* retain their values
            preserved_fields = [fld.name for fld in related_model._meta.concrete_fields if fld != rel.field]
            self.related_imprints[rel] = update_qs.values(*preserved_fields)
        
    def assertRestDeleted(self):
        """ Assert whether the other records were deleted after the merge. """
        qs = self.qs.exclude(pk=self.original.pk)
        if qs.exists():
            raise AssertionError('Merged records were not deleted: {}'.format(str(qs)))
        
    def assertOriginalExpanded(self, expand_original = True):
        """ Assert whether the original's values were expanded by the merged records correctly. """
        #TODO: what about changes provoked by passing a custom update_data dict to utils.merge_records?
        updateable_fields = self.original.get_updateable_fields()
        for fld_name, value in self.qs.filter(pk=self.original.pk).values()[0].items():
            if expand_original and fld_name in updateable_fields:
                # Change possible, but ONLY if any other of the merged records have values for these fields
                # which is implied by that field's name not showing up in their respective updateable_fields
                if any(fld_name not in other_updateable_fields
                        for other_updateable_fields
                        in [merge_record.get_updateable_fields() for merge_record in self.merge_records]):
                    expected_values = [getattr(merge_record, fld_name) for merge_record in self.merge_records]
                    if value not in expected_values:
                        raise AssertionError(
                            'Expected change did not occur: value of field {} did not change. Expected possible values: {}'.format(
                                fld_name, str(expected_values)))
            else:
                # No change expected since this field is not in updateable_fields
                old_value = getattr(self.original, fld_name)
                if old_value != value:
                    # A value has changed although it shouldn't have changed
                    raise AssertionError('Unexpected change with expand_original = {}: value of field {} changed from {} to {}.'.format(
                        str(expand_original), fld_name, str(old_value), str(value)))
        
    def assertRelatedChanges(self):
        for rel, related_valdicts in self.related_imprints.items():
            related_model = rel.field.model
            pk_name = related_model._meta.pk.name
            related_valdict_seen = []
            qs = getattr(self.original,rel.get_accessor_name()) 
            unseen_qs = qs.all()
            for related_valdict in related_valdicts:
                rel_pk = related_valdict.pop(pk_name)
                related_valdict_seen.append(related_valdict)
                unseen_qs = unseen_qs.exclude(**related_valdict)
                if not qs.filter(pk=rel_pk).exists(): 
                    # UNIQUE CONSTRAINTS might have 'dropped' some duplicate related objects: look for an equivalent object
                    c = qs.filter(**related_valdict).count()
                    if c==0:
                        # No equivalent objects are found in this set, we have lost data
                        raise AssertionError('Relation-Change did not occur for related object {}:{}.'.format(related_model._meta.model_name, str(rel_pk)))
                    elif c>1:
                        # Multiple equivalent objects were found
                        raise AssertionError('Multiple ({}) occurrences for related object {}:{} found.'.format(str(c), related_model._meta.model_name, str(rel_pk)))
                
            if unseen_qs.exists():
                # NEW related objects were added
                raise AssertionError('Unexpected additional {} relation-changes occurred: {}'.format(str(unseen_qs.count()), str(unseen_qs)))

