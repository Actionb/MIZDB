from unittest import expectedFailure, skip
from itertools import chain
import contextlib
import re

from django.test import TestCase, SimpleTestCase, Client, tag
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.http import unquote
from django.utils.encoding import force_text
from django.utils.translation import gettext, gettext_lazy
from django import forms

from DBentry.models import *
from DBentry.constants import *
from DBentry.sites import miz_site

from .mixins import *

class MyTestCase(TestCase):
            
    @contextlib.contextmanager
    def assertNotRaises(self, exceptions):
        # assert that the body does NOT raise one of the passed exceptions.
        raised = None
        try:
            yield
        except Exception as e:
            raised = e
            
        if raised and issubclass(raised.__class__, exceptions):
            self.fail("{} raised.".format(raised.__class__.__name__))
        
    def assertDictKeysEqual(self, d1, d2):
        t = "dict keys missing from {d}: {key_diff}"
        msg = ''
        key_diff = set(d1.keys()) - set(d2.keys())
        if key_diff:
            msg = t.format(d='d2', key_diff=str(key_diff))
        
        key_diff = set(d2.keys()) - set(d1.keys())
        if key_diff:
            if msg:
                msg += '\n'
            msg +=  t.format(d='d1', key_diff=str(key_diff))
        if msg:
            raise AssertionError(msg)
    
    def assertDictsEqual(self, dict1, dict2, msg=''):
        from django.http.request import QueryDict
        d1 = dict1.copy()
        d2 = dict2.copy()
        if isinstance(d1, QueryDict) and not isinstance(d2, QueryDict) or isinstance(d2, QueryDict) and not isinstance(d1, QueryDict):
            for d in [d1, d2]:
                # forcefully convert QueryDicts
                try:
                    d = d.dict()
                except:
                    continue
        self.assertDictKeysEqual(d1, d2)
        
        t = "dict values differ for key {k}: \n{v1} \n!=\n{v2}\n\n\n"
        msg = ''
        for k, v in d1.items():
            v1 = v
            v2 = d2.get(k)
            if isinstance(v1, dict) and isinstance(v2, dict):
                try:
                    self.assertDictsEqual(v1, v2)
                except AssertionError as e:
                    msg += "subdicts for key {k} differ: {msg}\n\n\n".format(k=k, msg=e.args[0])
            else:
                v1 = str(v1)
                v2 = str(v2)
                if v1 != v2:
                    msg += t.format(k=k, v1=v1, v2=v2)
        if msg:
            raise AssertionError(msg)
            
class DataTestCase(TestDataMixin, MyTestCase):
    pass
         
class UserTestCase(MyTestCase):
    
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
        
    def assertMessageSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} not found in messages: {}".format(expected_message,  [m[:len(expected_message)+5] + "[...]" for m in messages])
        if not any(m.startswith(expected_message) for m in messages):
            raise AssertionError(error_msg)
        #self.assertTrue(any(m.startswith(expected_message) for m in messages), error_msg)
        
    def assertMessageNotSent(self, request, expected_message):
        messages = [str(msg) for msg in get_messages(request)]
        error_msg = "Message {} found in messages: {}".format(expected_message,  [m[:len(expected_message)+5] + "[...]" for m in messages])
        if any(m.startswith(expected_message) for m in messages):
            raise AssertionError(error_msg)
        
    
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
        
    def get_action_func(self, action_name):
        for action in self.model_admin.actions: 
            func, name, desc = self.model_admin.get_action(action) 
            if name == self.action:
                return func 
        
    def call_action(self, action_name, objs, data=[]):
        from django.db.models.query import QuerySet
        if isinstance(objs, QuerySet):
            objs = objs.values_list('pk', flat=True)
        from django.contrib.admin import helpers    
        request_data = {'action':action_name, helpers.ACTION_CHECKBOX_NAME : objs}
        for other_dict in data:
            request_data.update(other_dict)
        return self.client.post(self.changelist_path, data=request_data)
        

##############################################################################################################
# TEST_FORMS TEST CASES
##############################################################################################################
class FormTestCase(MyTestCase, CreateFormMixin):
    
    def assertFormValid(self, form):
        if not form.is_valid():
            raise AssertionError('Form invalid. Form errors: {}'.format([(k,v) for k,v in form.errors.items()]))
            
    def assertFormInvalid(self, form):
        if form.is_valid():
            raise AssertionError('Form valid when expected to be invalid')
            
class ModelFormTestCase(TestDataMixin, FormTestCase):
    
    fields = None
    test_data_count = 1
    add_relations = False
    
    def get_form(self, **kwargs):
        return forms.modelform_factory(self.model, form=self.form_class, fields=self.fields)(**kwargs)
        

##############################################################################################################
# TEST_UTILS TEST CASES
##############################################################################################################
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
        
        # These are the related objects (or rather: their primary keys) that belong to original
        self.original_related_imprints = {}
        
        # These are the related objects (as val_dicts) that are affected by the merge and should end up being related to original
        self.related_imprints = {}
        for rel in self.model._meta.related_objects:
            related_model = rel.field.model
            self.original_related_imprints[rel] = getattr(self.original, rel.get_accessor_name()).values_list('pk', flat=True)
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
        self.assertLoggedDeletion(self.merge_records)
        
    def assertOriginalExpanded(self, expand_original = True):
        """ Assert whether the original's values were expanded by the merged records correctly. """
        #TODO: what about changes provoked by passing a custom update_data dict to utils.merge_records?
        updateable_fields = self.original.get_updateable_fields()
        change_message_fields = set()
        for fld_name, value in self.qs.filter(pk=self.original.pk).values()[0].items():
            if expand_original and fld_name in updateable_fields:
                # Change possible, but ONLY if any other of the merged records have values for these fields
                # which is implied by that field's name not showing up in their respective updateable_fields
                if any(fld_name not in other_updateable_fields
                        for other_updateable_fields
                        in [merge_record.get_updateable_fields() for merge_record in self.merge_records]):
                    change_message_fields.add(fld_name)
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
        if expand_original:
            self.assertLoggedChange(self.original, fields=change_message_fields)
        
    def assertRelatedChanges(self):
        """ Assert that the original is now related to all object that were related to the merge_records. """
        added_rel_object = set()
        for rel, related_valdicts in self.related_imprints.items():
            related_model = rel.field.model
            pk_name = related_model._meta.pk.name
            related_valdict_seen = [] #NOTE: this is not used for anything
            qs = getattr(self.original,rel.get_accessor_name()) 
            unseen_qs = qs.all()
            for related_valdict in related_valdicts:
                rel_pk = related_valdict.get(pk_name)
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
                    else:
                        added_rel_object.add((rel, qs.get(**related_valdict)))
                else:
                    added_rel_object.add((rel, qs.get(pk=rel_pk)))
                
            if unseen_qs.exists():
                # NEW related objects were added
                raise AssertionError('Unexpected additional {} relation-changes occurred: {}'.format(str(unseen_qs.count()), str(unseen_qs)))
        for rel, related_obj in added_rel_object:
            # Exempt related objects that were already related to original from the log assertions
            if related_obj.pk not in self.original_related_imprints[rel]:
                self.assertLoggedAddition(self.original, related_obj)
                self.assertLoggedChange(related_obj, rel.field.name)
