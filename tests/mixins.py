from django.contrib.admin.models import LogEntry, ContentType, ADDITION, CHANGE, DELETION
from django.contrib.admin.options import get_content_type_for_model

# TODO: remove: just override get_form_class on the test case classes that use this mixin
# class CreateFormViewMixin(CreateFormMixin, CreateViewMixin):
#     """Use the form_class given in view_class as the form's class."""
#
#
#     def get_form_class(self):
#         if getattr(self.view_class, 'form_class', None) is not None:
#             return self.view_class.form_class
#         else:
#             return super(CreateFormViewMixin, self).get_form_class()
#

# noinspection PyPep8Naming
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
        #
        # False negative:
        #   AssertionError: LogEntry for ADDITION missing on objects: [<Video: Original>], model: (video).
        # Filter parameters used:
        # [('action_flag', 1), ('change_message', '[{"added": {"name": "video-band-Beziehung", "object": "Video_band object (7)"}}]'), ('content_type__pk', 55), ('object_id', 32)]; video
        # LogEntry values:
        # [('action_flag', 1), ('change_message', '[{"added": {"object": "Video_band object (7)", "name": "video-band-Beziehung"}}]'), ('content_type__pk', 55), ('object_id', '32')]; video
        #
        # Differences:
        #   - the order of the keywords in change_message: (name, object) vs (object, name)
        #   - object_id type: int vs string

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
