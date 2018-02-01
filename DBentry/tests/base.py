from unittest import expectedFailure, skip
from itertools import chain

from django.test import TestCase, SimpleTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.http import unquote
from django import forms

from DBentry.models import *
from DBentry.constants import *
from DBentry.sites import miz_site

from .mixins import *

class ModelTestCase(TestDataMixin, TestCase):
    pass
         
class UserTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        super(UserTestCase, cls).setUpTestData()
        cls.super_user = User.objects.create_superuser(username='superuser', email='testtest@test.test', password='test1234')
        cls.staff_user = User.objects.create_user(username='staff', password='Stuff', is_staff = True)
        cls.noperms_user = User.objects.create_user(username='Beep', password='Boop')
        cls.users = [cls.super_user, cls.staff_user, cls.noperms_user]
        
    def setUp(self):
        super(UserTestCase, self).setUp()
        self.client.force_login(self.super_user) # super_user logged in by default

class RequestTestCase(UserTestCase):
    
    path = ''
    
    def post_request(self, path=None, data=None, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.post(path or self.path, data).wsgi_request
    
    def get_request(self, path=None, data=None, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.get(path or self.path, data).wsgi_request
    
class ViewTestCase(RequestTestCase, CreateViewMixin):
        pass
        
class AdminTestCase(TestDataMixin, RequestTestCase):
    
    admin_site = miz_site
    model_admin_class = None
    
    changelist_path = ''
    change_path = ''
    add_path = ''
    
    @classmethod
    def setUpTestData(cls):
        super(AdminTestCase, cls).setUpTestData()
            
        if not cls.changelist_path:
            cls.changelist_path = reverse('admin:DBentry_{}_changelist'.format(cls.model._meta.model_name))
        if not cls.change_path:
            cls.change_path = unquote(reverse('admin:DBentry_{}_change'.format(cls.model._meta.model_name), args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse('admin:DBentry_{}_add'.format(cls.model._meta.model_name))
    
    def setUp(self):
        super(AdminTestCase, self).setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)
        
    def assertMessageSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        self.assertTrue(expected_message in messages) 
        
class ActionTestCase(AdminTestCase):
    
    action = None
    
    def get_action_func(self):
        # the 'action' attribute can be either a name or a callable
        for a in self.model_admin.actions:
            func, name, desc = self.model_admin.get_action(a)
            if name == self.action or func == self.action:
                return func
    
    def setUp(self):
        super(ActionTestCase, self).setUp()
        self.action_func = self.get_action_func()

class ACViewTestCase(ViewTestCase):
    
    model = None
    create_field = None
    
    def view(self, request=None, args=None, kwargs=None, model = None, create_field = None, forwarded = None, q = None):
        #DBentry.ac.views behave slightly different in their as_view() method
        self.view_class.model = model or self.model
        self.view_class.create_field = create_field or self.create_field
        self.view_class.forwarded = forwarded or {}
        self.view_class.q = q or ''
        return super(ACViewTestCase, self).view(request, args, kwargs)

##############################################################################################################
# TEST_FORMS TEST CASES
##############################################################################################################
class FormTestCase(TestCase, CreateFormMixin):
    pass
            
class ModelFormTestCase(TestDataMixin, FormTestCase):
    
    fields = None
    test_data_count = 1
    add_relations = False
    
    def get_form(self, **kwargs):
        return forms.modelform_factory(self.model, form=self.form_class, fields=self.fields)(**kwargs)
        

##############################################################################################################
# TEST_UTILS TEST CASES
##############################################################################################################
class MergingTestCase(TestDataMixin, TestCase):
    
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
        self.ids = [self.original.pk] + [merge_record.pk for merge_record in self.merge_records] #TODO: needed in self? huh?!
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
