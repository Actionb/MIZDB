from django import template
from django.conf import settings
from django.contrib.auth import get_permission_codename

register = template.Library()


@register.simple_tag
def urlname(name, opts=None):
    """
    Return the 'url name' for the given name in the current namespace.

    If passing the second argument `opts`, prepend app_label and model_name to
    the name.
    """
    if opts:
        name = f"{opts.app_label}_{opts.model_name}_{name}"
    return f"{settings.SITE_NAMESPACE}:{name}"


@register.simple_tag
def has_perm(user, action, opts):
    """Return True if the given user has a certain permission to an object."""
    codename = get_permission_codename(action, opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename))
