
from django.contrib.admin.models import LogEntry, ContentType, ADDITION, CHANGE, DELETION
from django.utils.encoding import force_text

from DBentry.factory import make, batch

class TestDataMixin(object):
    
    model = None
    queryset = None
    test_data = None
    test_data_count = 0
    add_relations = True
    raw_data = None
    fixtures = ['monat.json']
    
    @classmethod
    def setUpTestData(cls):
        super(TestDataMixin, cls).setUpTestData()
        if cls.test_data is None:
            cls.test_data = []
        
        if cls.raw_data:
            if isinstance(cls.raw_data, dict):
                for pk, values in cls.raw_data.items():
                    try:
                        cls.test_data.append(make(cls.model, pk = pk, **values))
                    except TyperError:
                        # pk is included in values
                        cls.test_data.append(make(cls.model, **values))
            else:
                for values in cls.raw_data:
                    cls.test_data.append(make(cls.model, **values))
            
        if cls.test_data_count:
            cls.test_data.extend(list(batch(cls.model, cls.test_data_count)))
        for c, obj in enumerate(cls.test_data, 1):
            setattr(cls, 'obj' + str(c), obj)
        
    def setUp(self):
        super(TestDataMixin, self).setUp()
        for c, obj in enumerate(self.test_data, 1):
            obj.refresh_from_db()
            setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk))
        self.queryset = self.model.objects.all()
        
class CreateViewMixin(object):
    """
    Simulate the view being instantiated through as_view()().
    """
    
    view_class = None
    
    def view(self, request=None, args=None, kwargs=None, **initkwargs):
        #TODO: rename method to get_view
        #TODO: swap instantiation and attribute settings around ( set attributes on the instance, not the class )
        self.view_class.request = request
        self.view_class.args = args or []
        self.view_class.kwargs = kwargs or {}
        return self.view_class(**initkwargs)
        
    def get_dummy_view_class(self, bases=None, attrs=None):
        attrs = attrs or getattr(self, 'view_attrs', {})
        bases = bases or getattr(self, 'view_bases', ())
        if not isinstance(bases, (list, tuple)):
            bases = (bases, )
        return type("DummyView", bases, attrs)
        
    def get_dummy_view(self, bases=None, attrs=None, **initkwargs):
        return self.get_dummy_view_class(bases, attrs)(**initkwargs)

class CreateFormMixin(object):
    """
    Quickly create forms.
    """
    
    form_class = None
    dummy_fields = {}
    valid_data = {}
    
    def get_form_class(self):
        return self.form_class
    
    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        return form_class(**kwargs)
        
    def get_valid_form(self):
        form = self.get_form(data=self.valid_data.copy())
        if self.valid_data and not form.is_valid():
            raise Exception('self.valid_data did not contain valid data! form errors: {}'.format([(k,v) for k,v in form.errors.items()]))
        return form
    
    def get_dummy_form(self, fields=None, **form_initkwargs):
        fields = fields or self.dummy_fields
        return type('DummyForm', (self.form_class, ), fields.copy())(**form_initkwargs)
        
class CreateFormViewMixin(CreateFormMixin, CreateViewMixin):
    """
    Attempts to use the form_class given in view_class as the form's class.
    """   
        
    def get_form_class(self):
        if getattr(self.view_class, 'form_class', None) is not None:
            return self.view_class.form_class
        else:
            return super(CreateFormViewMixin, self).get_form_class()
            

class LoggingTestMixin(object):
    """
    Provides TestCases with Assertions that verify that a change to model objects is being logged.
    """
    
    def assertLogged(self, objects, action_flag, **kwargs):
        from django.contrib.admin.options import get_content_type_for_model
        
        if not LogEntry.objects.exists():
            raise AssertionError("LogEntry table is empty!")
        
        unlogged = []
        if not isinstance(objects, (list, tuple, set)):
            objects = [objects]
            
        # we need the content_type as a filter parameter here, or we're going to match everything
        # if objects contains model instances, they will set the content_type to their respective type
        content_type = kwargs.pop('content_type', None)
        if content_type is None:
            model = kwargs.pop('model', None) or getattr(self, 'model', None)
            if model is None:
                from django import models
                if not isinstance(objects[0], models.Model):
                    raise AttributeError("You must provide a model class either through kwargs or by setting a model attribute on the TestCase.")
                else:
                    model = objects[0].__class__
            content_type = get_content_type_for_model(model)
        
        for obj in objects:
            if isinstance(obj, int):
                pk = obj
            else:
                pk = obj.pk
                # obj is a model instance, use its model class to get the correct content_type
                content_type = get_content_type_for_model(obj._meta.model)
                
            filter_params = dict(object_id=pk, content_type__pk=content_type.pk, action_flag=action_flag)
            filter_params.update(**kwargs)
            qs = LogEntry.objects.filter(**filter_params)
            if not qs.exists(): 
                unlogged.append((obj, filter_params))
                continue
            if qs.count()>1:
                msg = "Could not verify uniqueness of LogEntry for object {object}.".format(object=object)
                msg += "\nNumber of matching logs: {count}.".format(count = qs.count())
                msg += "\nFilter parameters used: "
                msg += "\n{}; {}".format(sorted(filter_params.items()), ContentType.objects.get_for_id(filter_params['content_type__pk']).model)
                msg += "\nLogEntry values: "
                for l in LogEntry.objects.order_by('pk').filter(**filter_params).values('pk', *list(filter_params)):
                    pk = l.pop('pk')
                    ct_model = ContentType.objects.get_for_id(l['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(l.items()), ct_model)
                msg += "\nchange_messages: "
                for l in LogEntry.objects.order_by('pk').filter(**filter_params):
                    msg += "\n{}: {}".format(str(l.pk), l.get_change_message())
                msg += "\nCheck your test method or state of LogEntry table."
                raise AssertionError(msg) 
        if unlogged:
            msg = "LogEntry for {op} missing on objects: {unlogged_objects}, model: ({model_name}).".format(
                op = ['ADDITION', 'CHANGE', 'DELETION'][action_flag-1], 
                unlogged_objects = [i[0] for i in unlogged], 
                model_name = model._meta.model_name, 
            )  
            
            for obj, filter_params in unlogged:
                msg += "\nFilter parameters used: "
                msg += "\n{}; {}".format(sorted(filter_params.items()), ContentType.objects.get_for_id(filter_params['content_type__pk']).model)
                msg += "\nLogEntry values: "
                for l in LogEntry.objects.order_by('pk').values('pk', *list(filter_params)):
                    pk = l.pop('pk')
                    ct_model = ContentType.objects.get_for_id(l['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(l.items()), ct_model)
                msg += "\nchange_messages: "
                for l in LogEntry.objects.order_by('pk'):
                    msg += "\n{}: {}".format(str(l.pk), l.get_change_message())
            if hasattr(self, 'fail'):
                self.fail(msg)
            else:
                raise AssertionError(msg)
    
    def assertLoggedAddition(self, object, related_obj=None, **kwargs):
        """
        Assert that `object` has a LogEntry with action_flag == ADDITION.
        """
        # Do not overwrite any change_message filter_params (f.ex. change_message__contains) already set through kwargs
        if not any(k.startswith('change_message') for k in kwargs):
            msg = {"added": {}}
            if related_obj:
                msg['added'].update({
                    'name': force_text(related_obj._meta.verbose_name),
                    'object': force_text(related_obj),
                })
            kwargs['change_message'] = str([msg]).replace("'", '"')
        self.assertLogged(object, ADDITION, **kwargs)
    
    def assertLoggedChange(self, object, fields=None, related_obj=None, **kwargs):
        """
        Assert that `object` has a LogEntry with action_flag == CHANGE.
        """
        # Do not overwrite any change_message filter_params (f.ex. change_message__contains) already set through kwargs
        if not any(k.startswith('change_message') for k in kwargs):            
            if fields:
                if isinstance(fields, str):
                    fields = [fields]
                if not isinstance(fields, list):
                    fields = list(fields)
                msg = {'changed': {'fields': sorted(fields)}}
                if related_obj:
                    msg['changed'].update({
                        'name': force_text(related_obj._meta.verbose_name),
                        'object': force_text(related_obj),
                    })
                kwargs['change_message'] = str([msg]).replace("'", '"')
        self.assertLogged(object, CHANGE, **kwargs)
        
    def assertLoggedDeletion(self, objects, **kwargs):
        self.assertLogged(objects, DELETION, **kwargs)
