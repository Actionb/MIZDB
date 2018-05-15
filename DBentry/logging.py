from django.contrib.admin.options import get_content_type_for_model
from django.utils.encoding import force_text
from django.contrib.admin.models import ADDITION, CHANGE, DELETION

#TODO: save user name instead of user pk
#TODO: log_addition, log_change and log_deletion should fail silently, not the mixin methods?

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
    
def fail_silently(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError:
            return None
    return wrap
    

class LoggingMixin(object):
    #TODO: log_change should also log the old value
    """
    A mixin for views to log changes to model objects.
    """
    
    @fail_silently
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
    
    @fail_silently
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
        
    @fail_silently
    def log_deletion(self, obj):
        """
        Logging the deletion of an object.
        """
        return log_deletion(self.request, obj, obj.__repr__())
      
    def log_add(self, obj, rel, related_obj):
        """
        Logging of adding via related_managers.add(): obj.reverse_related_manager.add(related_obj).
        We want to log the addition of a related_obj on the target of the relation 
        and the change of the field of related_obj on the source of the relation.
        """
        logs = []
        logs.append(self.log_addition(obj, related_obj)) #TODO: is this even necessary? ausgabe.bestand_set: the ausgabe history should contain additions
        logs.append(self.log_change(related_obj, rel.field.name))
        return logs
        
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
            if isinstance(update_data, dict):
                fields = list(update_data.keys())
            else:
                fields = update_data
            log = self.log_change(obj, fields)
            logs.append(log)
        return logs

def get_logger(request):
    """
    Helper function to offer LoggingMixin's functionality to non-views.
    If request is None, all the log_X methods will fail silently.
    """
    l = LoggingMixin()
    l.request = request
    return l
