from dbentry.actions.views import MergeView
from dbentry.site.views.delete import DeleteSelectedView
from dbentry.utils import permission as perms
from dbentry.utils.permission import has_delete_permission


def action(permission_func=None, label="", description=""):
    """
    Decorator for action callables that adds a label, description and a
    permission check attribute to the callable.

    Args:
        permission_func: a callable that checks whether the user has
            permission to use this action
        label: a label text for the action
        description: a short description of what the action does
    """

    def decorator(func):
        def has_permission(*args, **kwargs):
            if permission_func:
                return permission_func(*args, **kwargs)
            return True

        func.has_permission = has_permission
        func.label = label
        func.description = description
        return func

    return decorator


@action(
    permission_func=has_delete_permission,
    label="Löschen",
    description="Ausgewählte Objekte löschen",
)
def delete(view, request, queryset):
    return DeleteSelectedView.as_view(model=queryset.model, queryset=queryset)(request)


def has_merge_permission(user, opts):
    return user.has_perm(perms.get_perm("merge", opts))


@action(
    permission_func=has_merge_permission,
    label="Zusammenfügen",
    description="Die ausgewählten Objekte in einziges Objekt zusammenfügen",
)
def merge_records(view, request, queryset):
    return MergeView.as_view(view=view, queryset=queryset)(request)
