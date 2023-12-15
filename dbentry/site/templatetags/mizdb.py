from urllib.parse import parse_qsl, unquote, urlparse, urlunparse

from django import template
from django.contrib.auth import get_permission_codename
from django.urls import Resolver404, get_script_prefix, resolve, reverse, NoReverseMatch
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from mizdb_tomselect.views import IS_POPUP_VAR

from dbentry.site.renderer import TabularInlineFormsetRenderer
from dbentry.utils import url
from dbentry.utils.html import create_hyperlink

register = template.Library()


@register.filter
def urlname(opts, name):  # pragma: no cover
    """
    Return the 'url name' for the given name/action and model options.
        {opts.app_label}_{opts.model_name}_{name}

    Usage:
        {% url opts|urlname:'add' %}
    """
    return url.urlname(name, opts)


@register.simple_tag
def paginator_url(changelist, i):  # pragma: no cover
    """Return the query string for the i-th result page of the given changelist."""
    from dbentry.site.views.base import PAGE_VAR  # avoid circular imports

    return changelist.get_query_string(new_params={PAGE_VAR: i})


@register.simple_tag
def has_perm(user, action, opts):  # pragma: no cover
    """Return True if the given user has a certain permission to an object."""
    codename = get_permission_codename(action, opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename))


@register.simple_tag
def has_module_perms(user, opts):
    """Return True if user_obj has any permissions in the given app_label."""
    return user.has_module_perms(opts.app_label)


@register.simple_tag
def get_bound_field(form, field_name):  # pragma: no cover
    """Return the form's bound field with the given field_name."""
    return form[field_name]


@register.simple_tag(takes_context=True)
def add_preserved_filters(context, base_url):
    """
    MIZDB version of the django admin add_preserved_filters tag that appends
    previous changelist filter query parameters to URLs.
    """
    opts = context.get("opts")
    preserved_filters = context.get("preserved_filters")

    parsed_url = list(urlparse(base_url))
    parsed_qs = dict(parse_qsl(parsed_url[4]))
    merged_qs = {}

    if opts and preserved_filters:
        preserved_filters = dict(parse_qsl(preserved_filters))
        # Get the (url) name of the view targeted by the base_url. If base_url
        # leads back to the changelist (f.ex. when saving a model object), we
        # need to parse the preserved filters portion of the initial query
        # string and add them to the result query string directly.
        match_url = f"/{unquote(base_url).partition(get_script_prefix())[2]}"
        try:
            match = resolve(match_url)
        except Resolver404:  # pragma: no cover
            pass
        else:
            changelist_url = url.urlname("changelist", opts)
            if match.url_name == changelist_url and "_changelist_filters" in preserved_filters:
                preserved_filters = dict(parse_qsl(preserved_filters["_changelist_filters"]))

        merged_qs.update(preserved_filters)

    merged_qs.update(parsed_qs)

    parsed_url[4] = urlencode(merged_qs)
    return urlunparse(parsed_url)


@register.simple_tag
def reset_ordering_link(changelist):
    """Provide a link that resets the ordering of the changelist results."""
    from dbentry.site.views.base import ORDER_VAR

    if ORDER_VAR not in changelist.request.GET:
        return ""
    params = dict(changelist.request.GET.items())
    del params[ORDER_VAR]
    return mark_safe(f'<span class="small ms-2"><a href="?{urlencode(params)}">Sortierung zurücksetzen</a></span>')


@register.simple_tag
def formset_has_errors(formset):
    """Return whether the formset data contains errors."""
    if not formset.is_bound:
        return False  # Data can't have errors if there is no data.
    else:
        return not formset.is_valid()


@register.simple_tag
def get_actionlist_item(entry):
    """
    Return the template context for the 'recent actions' list item of the given
    LogEntry.
    """
    change_link = entry.object_repr
    if not entry.is_deletion():
        try:
            change_link = create_hyperlink(
                reverse(urlname(entry.content_type.model_class()._meta, "change"), args=[entry.object_id]),
                entry.object_repr,
            )
        except NoReverseMatch:  # pragma: no cover
            pass
    if entry.is_addition():
        title = "Hinzugefügt"
        image = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-plus text-success me-1"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>'  # noqa
    elif entry.is_change():
        title = "Geändert"
        image = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-edit text-warning me-1"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'  # noqa
    else:
        title = "Gelöscht"
        image = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-x text-danger me-1"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'  # noqa
    return {"title": title, "image": mark_safe(image), "change_link": change_link}


@register.simple_tag
def tabular_inline_formset(formset, **kwargs):
    return TabularInlineFormsetRenderer(formset, **kwargs).render()


@register.simple_tag
def remove_popup_param(request):
    """Return a URL query string without IS_POPUP_VAR."""
    params = dict(request.GET.items()).copy()
    if IS_POPUP_VAR in params:
        del params[IS_POPUP_VAR]
    return f"?{urlencode(sorted(params.items()))}"
