from django import template
from django.contrib.auth import get_permission_codename

from dbentry.site.views import PAGE_VAR
from dbentry.utils import url

register = template.Library()


@register.filter
def urlname(opts, name):
    """
    Return the 'url name' for the given name/action and model options.
        {opts.app_label}_{opts.model_name}_{name}

    Usage:
        {% url opts|urlname:'add' %}
    """
    return url.urlname(name, opts)


@register.simple_tag
def paginator_url(cl, i):
    return cl.get_query_string({PAGE_VAR: i})


@register.simple_tag
def has_perm(user, action, opts):
    """Return True if the given user has a certain permission to an object."""
    codename = get_permission_codename(action, opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename))
