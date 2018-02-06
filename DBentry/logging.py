from django.contrib.admin.options import get_content_type_for_model
from django.utils.encoding import force_text
from django.contrib.admin.models import ADDITION, CHANGE, DELETION

def log_addition(request, object, message='[{"added": {}}]'):
    """
    from django.contrib.admin.options.ModelAdmin
    Log that an object has been successfully added.

    The default implementation creates an admin LogEntry object.
    """
    from django.contrib.admin.models import LogEntry
    return LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_text(object),
        action_flag=ADDITION,
        change_message=message,
    )

def log_change(request, object, message='[{"change": {}}]'):
    """
    from django.contrib.admin.options.ModelAdmin
    Log that an object has been successfully changed.

    The default implementation creates an admin LogEntry object.
    """
    from django.contrib.admin.models import LogEntry
    return LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_text(object),
        action_flag=CHANGE,
        change_message=message,
    )

def log_deletion(request, object, object_repr):
    """
    from django.contrib.admin.options.ModelAdmin
    Log that an object will be deleted. Note that this method must be
    called before the deletion.

    The default implementation creates an admin LogEntry object.
    """
    from django.contrib.admin.models import LogEntry
    return LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(object).pk,
        object_id=object.pk,
        object_repr=object_repr,
        action_flag=DELETION,
    )

class LoggingMixin(object):
    """
    A mixin for views to log changes to model objects.
    """
        
    def log_addition(self, obj, related_obj=None):
        """
        Logging of the creation of a single model instance or, if related_obj is given, logging of adding a M2M relation. 
        """
        msg = {"added": {}}
        if related_obj:
            msg['added'].update({
                'name': force_text(related_obj._meta.verbose_name),
                'object': force_text(related_obj),
            })
        return log_addition(self.request, obj, [msg])
    
    def log_change(self, obj, fields, related_obj=None):
        """
        Logging of the change(s) to a model instance or, if related_obj is given, of change(s) to a M2M relation. 
        """
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(fields, (list, tuple)):
            fields = list(fields)
        msg = {'changed': {'fields': sorted(fields)}}
        if related_obj:
            msg['changed'].update({
                'name': force_text(related_obj._meta.verbose_name),
                'object': force_text(related_obj),
            })
        return log_change(self.request, obj, [msg])
        
    def log_deletion(self, obj):
        """
        Logging the deletion of an object.
        """
        return log_deletion(self.request, obj, obj.__repr__())
        
    def log_add(self, obj, rel_or_field):
        """
        Logging of adding via related_managers.add().
        obj is the instance of the model defining the ForeignKey in the relation.
        rel_or_field can either be the relation or the ForeignKey field.
        """
        from django.db.models.fields.reverse_related import ForeignObjectRel
        fields = []
        if isinstance(rel_or_field, ForeignObjectRel):
            fields.append(rel_or_field.field.name)
        else:
            fields.append(rel_or_field.name)
        return self.log_change(obj, fields)
        
    def log_delete(self, queryset):
        """
        Logging deletes on a queryset.
        """
        logs = []
        for obj in queryset:
            log = self.log_deletion(obj)
            logs.append(log)
        return logs
        
    def log_update(self, queryset, update_data):
        """
        Logging updates on a queryset.
        """
        logs = []
        for obj in queryset:
            fields = list(update_data.keys())
            log = self.log_change(obj, fields)
            logs.append(log)
        return logs

def get_logger(request):
    """
    Helper function to offer LoggingMixin's functionality to non-views.
    """
    l = LoggingMixin()
    l.request = request
    return l
