from unittest import expectedFailure, skip
from unittest.mock import Mock, MagicMock, patch
from itertools import chain
from functools import partial
from collections import OrderedDict
import contextlib
import re

from django.test import TestCase, SimpleTestCase, Client, tag
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.http import unquote
from django.utils.encoding import force_text
from django.utils.translation import gettext, gettext_lazy, override as translation_override
from django import forms
from django.db.models.query import QuerySet

from DBentry.models import *
from DBentry.constants import *
from DBentry.sites import miz_site
from DBentry.factory import *

from .mixins import *

def mockv(value):
    return Mock(return_value=value)
    
def mockex(exception):
    return Mock(side_effect=exception)

class MyTestCase(TestCase):
            
    @contextlib.contextmanager
    def assertNotRaises(self, exceptions, msg = None):
        """
        Assert that the body does NOT raise one of the passed exceptions.
        """ 
        raised = None
        try:
            yield
        except Exception as e:
            raised = e
            
        if raised and issubclass(raised.__class__, exceptions):
            fail_txt = "{} raised.".format(raised.__class__.__name__)
            if msg:
                fail_txt += ':' + msg
            self.fail(fail_txt)
        
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
    
    def assertListEqualSorted(self, list1, list2, msg=None):
        self.assertListEqual(sorted(list1), sorted(list2), msg)
            
    def assertAllValues(self, values_list, value, msg=None):
        """
        Assert that `value` is equal to all items of `values_list`.
        """
        expected = [value for v in values_list]
        self.assertEqual(values_list, expected, msg)  # delivers more useful information on failure than self.assertTrue(all(v==value for v in values_list))
      
class DataTestCase(TestDataMixin, MyTestCase):
    
    # django's assertQuerysetEqual will transform the queryset's values according to function given by parameter `transform` (assertQuerysetEqual requires hashable objects).
    # This would end up converting dicts/tuples from queryset.values()/.values_list() into strings.
    # Obviously, this is not what we want, if we want to make comparing queryset.values()/.values_list() simple to use.
    # We could pass transform = lambda d: tuple(*d.items()) to assertQuerysetEqual, but that would require transforming `values` as well.
    
    def assertQSEqual(self, queryset, values, transform=str, ordered=False, msg=None):
        # Reconfiguration of the default parameters to values we use most in tests: reduces clutter
        # - the __str__ method is heavily used in our app, more than repr
        # - the tests usually do not care about the order of values
        if not isinstance(values, (list, tuple)):
            values = [values]
        self.assertQuerysetEqual(queryset, values, transform, ordered, msg)
        
    def assertQuerysetEqual(self, queryset, values, transform=repr, ordered=False, msg=None):
        # django's assertQuerysetEqual does not transform 'values' if it would be required
        if isinstance(values, QuerySet):
            values = map(transform, values)
        return super().assertQuerysetEqual(queryset, values, transform, ordered, msg)
        
    def assertPKListEqual(self, pk_list1, pk_list2):
        if isinstance(pk_list1, QuerySet):
            pk_list1 = list(pk_list1.values_list('pk', flat=True))
        if isinstance(pk_list2, QuerySet):
            pk_list2 = list(pk_list2.values_list('pk', flat=True))
        self.assertListEqualSorted(pk_list1, pk_list2)
        
    def assertQSValues(self, queryset, fields, values, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(values, (list, tuple)):
            # A list of tuples of (field, value) is expected.
            values = list(zip(fields, [values]*len(fields)))
            
        # Still call queryset.values(), but convert the results from a list of dicts to a list of tuples for easier comparison.
        qs_list = [tuple(*i.items()) for i in queryset.values(*fields)]
        self.assertListEqualSorted(qs_list, values, msg)
        
    def assertAllQSValues(self, queryset, fields, value, msg=None):
        from collections import Iterable
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(value, str) or not isinstance(value, Iterable):
            if len(fields)==1:
                value = (fields, value)
            else:
                raise TypeError("argument value must be an iterable")
                
        expected = [value] * queryset.count() if queryset.count() else [value]  # an empty queryset should assert as not equal to [value] and not as equal to [] 
        self.assertQSValues(queryset, fields, expected, msg)
        
    def assertQSValuesList(self, queryset, fields, values, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(values, (list, tuple)):
            values = [values]
        values_list = list(queryset.values_list(*fields, flat=len(fields)==1))
        self.assertListEqualSorted(values_list, values, msg)
        
    def assertAllQSValuesList(self, queryset, fields, value, transform=str, ordered=False, msg=None):
        if isinstance(fields, str):
            fields = [fields]
        expected = [value] * queryset.count() if queryset.count() else [value]  # an empty queryset should assert as not equal to [value] and not as equal to [] 
        self.assertQSValuesList(queryset, fields, expected, msg)
        
         
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
    
    def get_path(self):
        return self.path
    
    def post_request(self, path=None, data=None, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.post(path or self.get_path(), data).wsgi_request
    
    def get_request(self, path=None, data=None, user=None):
        self.client.force_login(user or self.super_user)
        return self.client.get(path or self.get_path(), data).wsgi_request
        
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
        if isinstance(objs, QuerySet):
            objs = objs.values_list('pk', flat=True)
        from django.contrib.admin import helpers    
        request_data = {'action':action_name, helpers.ACTION_CHECKBOX_NAME : objs}
        for other_dict in data:
            request_data.update(other_dict)
        return self.client.post(self.changelist_path, data=request_data)
        
    def get_changelist(self, request):
        list_display = self.model_admin.get_list_display(request)
        list_display_links = self.model_admin.get_list_display_links(request, list_display)
        list_filter = self.model_admin.get_list_filter(request)
        search_fields = self.model_admin.get_search_fields(request)
        list_select_related = self.model_admin.get_list_select_related(request)
        
        ChangeList = self.model_admin.get_changelist(request)
        cl = ChangeList(
            request, self.model, list_display,
            list_display_links, list_filter, self.model_admin.date_hierarchy,
            search_fields, list_select_related, self.model_admin.list_per_page,
            self.model_admin.list_max_show_all, self.model_admin.list_editable, self.model_admin,
        )
        return cl
        

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
        
        # These are the related objects that belong to original
        self.original_related = {}
        
        # These are the related objects that are affected by the merge and should end up being related to original
        self.merger_related = {}
        
        
        for rel in get_model_relations(self.model, forward = False):
            related_model, related_field = get_relation_info_to(self.model, rel)
                
            # These are the fields of the related_model that *should* retain their values
            preserved_fields = [
                fld.name 
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
        if expand_original:
            self.change_message_fields = change_message_fields # prepare for the logging assertion
            
    def assertOriginalExpandedLogged(self):
        self.assertLoggedChange(self.original, fields=getattr(self, 'change_message_fields', []))
            
    def assertRelatedChanges(self):
        """ Assert that the original is now related to all objects that were related to the merge_records. """
        added_rel_object = set()    # keeps track of every object that has been added to original
        #for (related_model, related_field), related_valdicts in self.merger_related.items():
        for rel in get_model_relations(self.model, forward = False):
            related_model, related_field = get_relation_info_to(self.model, rel)
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
                print('related_obj', related_obj)
                print(related_model, related_field)
                raise e
            self.assertLoggedChange(related_obj, related_field.name, self.original)
