from django.contrib.admin.models import LogEntry, ContentType, ADDITION, CHANGE, DELETION
from django.contrib.admin.options import get_content_type_for_model

from dbentry.factory import make, batch


# noinspection PyPep8Naming,PyUnresolvedReferences
class TestDataMixin(object):
    model = None
    queryset = None
    test_data = None
    test_data_count = 0
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
                        cls.test_data.append(make(cls.model, pk=pk, **values))
                    except TypeError:
                        # pk is included in values
                        cls.test_data.append(make(cls.model, **values))
            else:
                for values in cls.raw_data:
                    cls.test_data.append(make(cls.model, **values))

        if cls.test_data_count:
            cls.test_data.extend(list(batch(cls.model, cls.test_data_count)))
        cls._ids = []
        for c, obj in enumerate(cls.test_data, 1):
            setattr(cls, 'obj' + str(c), obj)
            cls._ids.append(obj.pk)

    def setUp(self):
        super(TestDataMixin, self).setUp()
        for c, obj in enumerate(self.test_data, 1):
            obj.refresh_from_db()
            setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk))
        self.queryset = self.model.objects.all()


class CreateViewMixin(object):
    """Simulate the view being instantiated through as_view()()."""

    view_class = None

    def get_view(self, request=None, args=None, kwargs=None, **initkwargs):
        view = self.view_class(**initkwargs)
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        view.setup(request, *args, **kwargs)
        return view

    def get_dummy_view_class(self, bases=None, attrs=None):
        if bases is None:
            bases = getattr(self, 'view_bases', ())
        if attrs is None:
            attrs = attrs or getattr(self, 'view_attrs', {})
        if not isinstance(bases, (list, tuple)):
            bases = (bases,)
        return type("DummyView", bases, attrs)

    def get_dummy_view(self, bases=None, attrs=None, **initkwargs):
        return self.get_dummy_view_class(bases, attrs)(**initkwargs)


class CreateFormMixin(object):
    """Quickly create forms."""

    form_class = None
    dummy_bases = None
    dummy_attrs = None
    valid_data = None

    def get_form_class(self):
        return self.form_class

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        return form_class(**kwargs)

    def get_valid_form(self):
        form = self.get_form(data=self.valid_data.copy())
        if self.valid_data and not form.is_valid():
            error_msg = 'self.valid_data did not contain valid data! form errors: {}'.format(
                [(k, v) for k, v in form.errors.items()])
            raise Exception(error_msg)
        return form

    def get_dummy_form_class(self, bases=None, attrs=None):
        if bases is None:
            bases = self.dummy_bases or (object,)
        if attrs and self.dummy_attrs:
            class_attrs = {**self.dummy_attrs, **attrs}
        elif attrs:
            class_attrs = attrs.copy()
        elif self.dummy_attrs:
            class_attrs = self.dummy_attrs.copy()
        else:
            class_attrs = {}
        return type('DummyForm', bases, class_attrs)

    def get_dummy_form(self, bases=None, attrs=None, **form_initkwargs):
        return self.get_dummy_form_class(bases, attrs)(**form_initkwargs)


class CreateFormViewMixin(CreateFormMixin, CreateViewMixin):
    """Use the form_class given in view_class as the form's class."""

    def get_form_class(self):
        if getattr(self.view_class, 'form_class', None) is not None:
            return self.view_class.form_class
        else:
            return super(CreateFormViewMixin, self).get_form_class()


# noinspection PyUnresolvedReferences,PyPep8Naming
class LoggingTestMixin(object):
    """
    Provide TestCases with assertions that verify that a change to model
    objects is being logged.
    """

    def assertLogged(self, objects, action_flag, change_message=None, **kwargs):
        if not LogEntry.objects.exists():
            raise AssertionError("LogEntry table is empty!")
        unlogged = []
        if not isinstance(objects, (list, tuple, set)):
            objects = [objects]
        # Prepare the change_message:
        if not change_message:
            if action_flag == ADDITION:
                change_message = [{"added": {}}]
            elif action_flag == CHANGE:
                change_message = [{"changed": {}}]
            elif action_flag == DELETION:
                change_message = [{"deleted": {}}]
        if not isinstance(change_message, str):
            change_message = str(change_message)
        change_message = change_message.replace("'", '"')

        # FIXME: occasionally this returns false negatives:
        # a log entry for the given filter parameters exists, but the queryset
        # still returns empty.
        # Only the order of change message dictionary keywords differ, but:
        #   a) the order of keywords should not matter for the query
        #   b) the difference might only exist in the error message; the sorting
        #       done on the filter parameter dictionary for the message might
        #       create the difference
        # 
        #   AssertionError: LogEntry for ADDITION missing on objects: [<Video: Original>], model: (video).
        # Filter parameters used:
        # [('action_flag', 1), ('change_message', '[{"added": {"name": "video-band-Beziehung", "object": "Video_band object (7)"}}]'), ('content_type__pk', 55), ('object_id', 32)]; video
        # LogEntry values:
        # [('action_flag', 1), ('change_message', '[{"added": {"object": "Video_band object (7)", "name": "video-band-Beziehung"}}]'), ('content_type__pk', 55), ('object_id', '32')]; video

        # FIXME: occasionally this returns false negatives:
        # a log entry for the given filter parameters exists, but the queryset
        # still returns empty.
        # Only the order of change message dictionary keywords differ, but:
        #   a) the order of keywords should not matter for the query
        #   b) the difference might only exist in the error message; the sorting
        #       done on the filter parameter dictionary for the message might
        #       create the difference
        # 
        #   AssertionError: LogEntry for ADDITION missing on objects: [<Video: Original>], model: (video).
        # Filter parameters used:
        # [('action_flag', 1), ('change_message', '[{"added": {"name": "video-band-Beziehung", "object": "Video_band object (7)"}}]'), ('content_type__pk', 55), ('object_id', 32)]; video
        # LogEntry values:
        # [('action_flag', 1), ('change_message', '[{"added": {"object": "Video_band object (7)", "name": "video-band-Beziehung"}}]'), ('content_type__pk', 55), ('object_id', '32')]; video

        # We need the content_type as a filter parameter here, or we're going
        # to match everything.
        for obj in objects:
            pk = obj.pk
            model = obj._meta.model
            content_type = get_content_type_for_model(model)
            filter_params = {
                'object_id': pk,
                'content_type__pk': content_type.pk,
                'action_flag': action_flag,
                'change_message': change_message
            }
            filter_params.update(**kwargs)
            qs = LogEntry.objects.filter(**filter_params)
            if not qs.exists():
                unlogged.append((obj, filter_params))
                continue
            if qs.count() > 1:
                msg = (
                    "Could not verify uniqueness of LogEntry for object {object}."
                    "\nNumber of matching logs: {count}."
                    "\nFilter parameters used: "
                    "\n{items}; {model}"
                    "\nLogEntry values: "
                ).format(
                    object=object,
                    count=qs.count(),
                    items=sorted(filter_params.items()),
                    model=ContentType.objects.get_for_id(
                        filter_params['content_type__pk']).model,
                )
                for values in (
                        LogEntry.objects
                                .order_by('pk')
                                .filter(**filter_params)
                                .values('pk', *list(filter_params))
                ):
                    pk = values.pop('pk')
                    ct_model = ContentType.objects.get_for_id(values['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(values.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by('pk').filter(**filter_params):
                    msg += "\n{}: {}".format(str(log_entry.pk), log_entry.get_change_message())
                msg += "\nCheck your test method or state of LogEntry table."
                raise AssertionError(msg)
        if unlogged:
            # noinspection PyUnboundLocalVariable
            msg = (
                "LogEntry for {op} missing on objects: {unlogged_objects}, "
                "model: ({model_name})."
            ).format(
                op=['ADDITION', 'CHANGE', 'DELETION'][action_flag - 1],
                unlogged_objects=[i[0] for i in unlogged],
                model_name=model._meta.model_name,
            )

            for _obj, filter_params in unlogged:
                msg += "\nFilter parameters used: "
                msg += "\n{}; {}".format(
                    sorted(filter_params.items()),
                    ContentType.objects.get_for_id(filter_params['content_type__pk']).model
                )
                msg += "\nLogEntry values: "
                for log_entry in LogEntry.objects.order_by('pk').values('pk', *list(filter_params)):
                    pk = log_entry.pop('pk')
                    ct_model = ContentType.objects.get_for_id(log_entry['content_type__pk']).model
                    msg += "\n{}: {}; {}".format(str(pk), sorted(log_entry.items()), ct_model)
                msg += "\nchange_messages: "
                for log_entry in LogEntry.objects.order_by('pk'):
                    msg += "\n{}: {}".format(str(log_entry.pk), log_entry.get_change_message())
            self.fail(msg)

    def assertLoggedAddition(self, obj, **kwargs):
        """Assert that `obj` has a LogEntry with action_flag == ADDITION."""
        self.assertLogged(obj, ADDITION, **kwargs)

    def assertLoggedChange(self, obj, **kwargs):
        """Assert that `object` has a LogEntry with action_flag == CHANGE."""
        self.assertLogged(obj, CHANGE, **kwargs)

    def assertLoggedDeletion(self, objects, **kwargs):
        self.assertLogged(objects, DELETION, **kwargs)
