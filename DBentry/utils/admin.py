from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.urls import reverse, NoReverseMatch
from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename
from django.core import exceptions

from DBentry.utils.models import get_model_from_string

def get_obj_link(obj, user, site_name='admin', include_name=True): #TODO: include_name == include_label??
    opts = obj._meta
    no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
                               force_text(obj))

    try:
        admin_url = reverse('%s:%s_%s_change'
                            % (site_name,
                               opts.app_label,
                               opts.model_name),
                            None, (quote(obj._get_pk_val()),)) #TODO: this is the getter of the 'pk' property!
    except NoReverseMatch:
        # Change url doesn't exist -- don't display link to edit
        return no_edit_link

    p = '%s.%s' % (opts.app_label,
                   get_permission_codename('change', opts))
    if not user.has_perm(p):
        return no_edit_link
    # Display a link to the admin page.
    if include_name:
        link = format_html('{}: <a href="{}">{}</a>', # include_name is more a label than... a 'name'
                           capfirst(opts.verbose_name),
                           admin_url,
                           obj)
    else:
        link = format_html('<a href="{}">{}</a>',
                           admin_url,
                           obj)           
    return link

def get_changelist_link(model, user, site_name = 'admin', obj_list = None):
    opts = model._meta
    try:
        url = reverse(
            '%s:%s_%s_changelist' % (site_name,opts.app_label,opts.model_name)
        )
    except NoReverseMatch:
        return ''
    p = '%s.%s' % (opts.app_label,
                   get_permission_codename('changelist', opts))
    if not user.has_perm(p):
        return ''
    if obj_list:
        url += '?id__in={}'.format(",".join([str(obj.pk) for obj in obj_list]))
    return format_html('<a href="{}">Liste</a>', url)      

def link_list(request, obj_list, SEP = ", "):
    """ Returns a string with html links to the objects in obj_list separated by SEP.
        Used in ModelAdmin
    """
    links = []
    for obj in obj_list:
        links.append(get_obj_link(obj, request.user, include_name=False))
    return format_html(SEP.join(links))

def get_model_admin_for_model(model, *admin_sites):
    from DBentry.sites import miz_site
    if isinstance(model, str):
        model = get_model_from_string(model)
    sites = admin_sites or [miz_site]
    for site in sites:
        if site.is_registered(model):
            return site._registry.get(model)        

def has_admin_permission(request, model_admin):
    if not model_admin.has_module_permission(request):
        return False
    perms = model_admin.get_model_perms(request)

    # Check whether user has any perm for this module.
    return True in perms.values()

def make_simple_link(url, label, is_popup, as_listitem = False):
    if is_popup:
        template = '<a href="{url}?_popup=1" onclick="return popup(this)">{label}</a>'
    else:
        template = '<a href="{url}" target="_blank">{label}</a>'
    if as_listitem:
        template = '<li>' + template + '</li>'
    return format_html(
        template, 
        url = url, 
        label = label
    )

def resolve_list_display_item(model_admin, item):
    """
    Helper function to resolve an item of the model_admin.list_display into
    a model field or a callable.

    Returns either:
        a model field of model_admin.model
        a callable (a function or a model_admin or model_admin.model method)
        None if the item could not be resolved
    """
    try:
        return model_admin.opts.get_field(item)
    except exceptions.FieldDoesNotExist:
        if callable(item):
            func = item
        elif hasattr(model_admin, item) and item != '__str__':
            func = getattr(model_admin, item)
        elif hasattr(model_admin.model, item):
            func = getattr(model_admin.model, item)
        else:
            func = None
        return func
