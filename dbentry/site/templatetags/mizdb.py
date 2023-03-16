from django import template
from django.contrib.auth import get_permission_codename

register = template.Library()


@register.filter
def urlname(opts, arg):
    return f"mizdb:{opts.app_label}_{opts.model_name}_{arg}"


@register.simple_tag
def has_perm(user, action, opts):
    """Return True if the given user has a certain permission to an object."""
    codename = get_permission_codename(action, opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename))
