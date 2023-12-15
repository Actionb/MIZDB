from django.conf import settings
from django.contrib.auth import get_permission_codename


def get_perm(action, opts):
    """Return the permission name in the form <app_label>.<codename>."""
    return f"{opts.app_label}.{get_permission_codename(action, opts)}"


def has_add_permission(user, opts) -> bool:
    return user.has_perm(get_perm("add", opts))


def has_change_permission(user, opts) -> bool:
    return user.has_perm(get_perm("change", opts))


def has_delete_permission(user, opts) -> bool:
    return user.has_perm(get_perm("delete", opts))


def has_view_permission(user, opts) -> bool:
    if settings.ANONYMOUS_CAN_VIEW:
        # Always allow viewing if that setting is True.
        return True
    return user.has_perm(get_perm("view", opts)) or has_change_permission(user, opts)
