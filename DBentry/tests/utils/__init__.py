from django.test import tag

from DBentry.tests.base import RequestTestCase
from DBentry.tests.mixins import LoggingTestMixin, TestDataMixin
from DBentry.utils.models import get_model_fields, get_model_relations, get_relation_info_to, get_updateable_fields


@tag('logging', 'merge')
class MergingTestCase(LoggingTestMixin, TestDataMixin, RequestTestCase): # Need a request object to create LogEntries 
    
    test_data_count = 3
    
    @classmethod
    def setUpTestData(cls):
        super(MergingTestCase, cls).setUpTestData()
        cls.original = cls.test_data[0]
        cls.merge_records = []
        for c, merge_record in enumerate(cls.test_data[1:], 1):
            setattr(cls, 'merge_record' + str(c), merge_record)
            cls.merge_records.append(merge_record)
        
    def setUp(self):
        super(MergingTestCase, self).setUp()
        self.request = self.get_request()
        self.ids = [self.original.pk] + [merge_record.pk for merge_record in self.merge_records]
        self.qs = self.model.objects.filter(pk__in=self.ids)
        
        # These are the related objects that belong to original
        self.original_related = {}
        
        # These are the related objects that are affected by the merge and should end up being related to original
        self.merger_related = {}
        
        
        for rel in get_model_relations(self.model, forward = False):
            related_model, related_field = get_relation_info_to(self.model, rel)
                
            # These are the fields of the related_model that *should* retain their values
            preserved_fields = [
                fld.attname 
                for fld in get_model_fields(
                    related_model, m2m = False, 
                    exclude = [related_field.name], primary_key = True
                    )
            ]
            
            # The values of the objects of the related model that are related to original
            self.original_related[(related_model, related_field)] = list(related_model.objects.filter(**{related_field.name:self.original}).values(*preserved_fields))  # list() to force evaluation

            # A queryset of all objects of the related model affected by the merge
            updated_qs = related_model.objects.filter(**{related_field.name + '__in':self.merge_records})
            
            # The values of the objects in the aforementioned queryset
            self.merger_related[(related_model, related_field)] = list(updated_qs.values(*preserved_fields)) # list() to force evaluation
          
    def assertRestDeleted(self):
        """ Assert whether the other records were deleted after the merge. """
        qs = self.qs.exclude(pk=self.original.pk)
        if qs.exists():
            raise AssertionError('Merged records were not deleted: {}'.format(str(qs)))
        self.deleted_records = self.merge_records # prepare for the logging assertion
        
    def assertRestDeletedLogged(self):
        self.assertLoggedDeletion(getattr(self, 'deleted_records', []))
        
    def assertOriginalExpanded(self, expand_original = True):
        """ Assert whether the original's values were expanded by the merged records correctly. """
        updateable_fields = get_updateable_fields(self.original)
        change_message_fields = set()
        for fld_name, value in self.qs.filter(pk=self.original.pk).values()[0].items():
            if expand_original and fld_name in updateable_fields:
                # Change possible, but ONLY if any other of the merged records have values for these fields
                # which is implied by that field's name not showing up in their respective updateable_fields
                if any(fld_name not in other_updateable_fields
                        for other_updateable_fields
                        in [get_updateable_fields(merge_record) for merge_record in self.merge_records]):
                    change_message_fields.add(fld_name)
                    expected_values = [getattr(merge_record, fld_name) for merge_record in self.merge_records]
                    if value not in expected_values:
                        raise AssertionError(
                            'Expected change did not occur: value of field {} did not change. Expected possible values: {}'.format(
                                fld_name, str(expected_values)))
            elif fld_name.startswith('_'):
                # A private field (possibly from ComputedNameModel). We cannot ascertain (or rather: should not need to worry about) whether this field's value should have changed or not.
                continue
            else:
                # No change expected since this field is not in updateable_fields
                old_value = getattr(self.original, fld_name)
                if old_value != value:
                    # A value has changed although it shouldn't have changed
                    raise AssertionError('Unexpected change with expand_original = {}: value of field {} changed from {} to {}.'.format(
                        str(expand_original), fld_name, str(old_value), str(value)))
        if change_message_fields:
            self.change_message_fields = change_message_fields # prepare for the logging assertion
            
    def assertOriginalExpandedLogged(self):
        if getattr(self, 'change_message_fields', None):
            self.assertLoggedChange(self.original, fields=getattr(self, 'change_message_fields', []))
            
    def assertRelatedChanges(self):
        """ Assert that the original is now related to all objects that were related to the merge_records. """
        added_rel_object = set()    # keeps track of every object that has been added to original
        #for (related_model, related_field), related_valdicts in self.merger_related.items():
        for rel in get_model_relations(self.model, forward = False):
            related_model, related_field = get_relation_info_to(self.model, rel)
            if related_model == self.model:
                # ignore self relations
                continue
            pk_name = related_model._meta.pk.name
            pks_seen = set()
            qs = related_model.objects.filter(**{related_field.name:self.original})  # queryset of objects that are now related to original
            
            # objects added from the other merged records
            for related_valdict in self.merger_related.get((related_model, related_field), []):
                rel_pk = related_valdict.pop(pk_name)
                pks_seen.add(rel_pk)
                if qs.filter(pk=rel_pk).count()!=1: 
                    # UNIQUE CONSTRAINTS might have 'dropped' some duplicate related objects: look for an equivalent object
                    equivalent_qs = qs.filter(**related_valdict)
                    c = equivalent_qs.count()
                    if c==0:
                        # No equivalent objects are found in this set, we have lost data
                        raise AssertionError('Relation-Change did not occur for related object {}:{}.'.format(related_model._meta.model_name, str(rel_pk)))
                    elif c>1:
                        # Multiple equivalent objects were found
                        raise AssertionError('Multiple ({}) occurrences for related object {}:{} found.'.format(str(c), related_model._meta.model_name, str(rel_pk)))
                    else:
                        added_rel_object.add(((related_model, related_field), equivalent_qs[0]))
                else:
                    added_rel_object.add(((related_model, related_field), qs.get(pk=rel_pk)))
                    
            # objects that were already related to original
            for related_valdict in self.original_related.get((related_model, related_field), []):
                rel_pk = related_valdict.pop(pk_name)
                pks_seen.add(rel_pk)
                if qs.filter(pk=rel_pk).count()!=1: 
                    # UNIQUE CONSTRAINTS might have 'dropped' some duplicate related objects: look for an equivalent object
                    equivalent_qs = qs.filter(**related_valdict)
                    c = equivalent_qs.count()
                    if c==0:
                        # No equivalent objects are found in this set, we have lost data
                        raise AssertionError('A related object of the original was dropped unexpectedly {}:{}.'.format(related_model._meta.model_name, str(rel_pk)))
                    elif c>1:
                        # Multiple equivalent objects were found
                        raise AssertionError('Multiple ({}) occurrences for related object {}:{} found.'.format(str(c), related_model._meta.model_name, str(rel_pk)))

            unseen_qs = qs.exclude(pk__in=pks_seen)
            if unseen_qs.exists():
                # NEW related objects were added
                raise AssertionError(
                    'Unexpected additional {} relation-changes occurred: {}'.format(
                        str(unseen_qs.count()), str(unseen_qs)
                    )
                )
                
        self.added_rel_object = added_rel_object

    def assertRelatedChangesLogged(self):
        # Assert that all changes/additions have been logged
        for (related_model, related_field), related_obj in getattr(self, 'added_rel_object', []):
            try:
                self.assertLoggedAddition(self.original, related_obj)
            except AssertionError as e:
                raise e
            self.assertLoggedChange(related_obj, related_field.name, self.original)
