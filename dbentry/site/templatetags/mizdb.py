from django import template
from django.contrib.auth import get_permission_codename

from dbentry.utils import url

register = template.Library()


@register.simple_tag
def urlname(name, opts=None, namespace=''):
    """
    Return the 'url name' for the given name/action.

    If model options ``opts`` is given, prepend app_label and model_name to
    the name:
        {opts.app_label}_{opts.model_name}_{name}
    If ``namespace`` is given, prepend the app namespace to the name:
        {namespace}:{name}
    """
    return url.urlname(name, opts, namespace)


@register.simple_tag
def has_perm(user, action, opts):
    """Return True if the given user has a certain permission to an object."""
    codename = get_permission_codename(action, opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename))
