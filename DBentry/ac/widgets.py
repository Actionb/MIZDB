from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.urls import reverse

from dal import autocomplete

from DBentry.utils import get_model_from_string

class WidgetCaptureMixin(object):
    
    def __init__(self, model_name, *args, **kwargs):
        self.model_name = model_name
        self.create_field = kwargs.pop('create_field', None)
        if 'url' not in kwargs:
            kwargs['url'] = 'accapture'
        super().__init__(*args, **kwargs)
    
    def _get_url(self):
        if self._url is None:
            return None

        if '/' in self._url:
            return self._url
        reverse_kwargs = {}
        if self.model_name:
            reverse_kwargs['model_name'] = self.model_name
        if self.create_field:
            reverse_kwargs['create_field'] = self.create_field
        return reverse(self._url, kwargs=reverse_kwargs)

    def _set_url(self, url):
        self._url = url

    url = property(_get_url, _set_url)
    
class MIZModelSelect2(WidgetCaptureMixin, autocomplete.ModelSelect2):
    pass
    
class MIZModelSelect2Multiple(WidgetCaptureMixin, autocomplete.ModelSelect2Multiple):
    pass

class EasyWidgetWrapper(RelatedFieldWidgetWrapper):
    
    def __init__(self, widget, related_model, remote_field_name = 'id', 
            can_add_related=True, can_change_related=True, can_delete_related=True):
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.can_add_related = can_add_related
        self.can_change_related = can_change_related
        self.can_delete_related = can_delete_related
        self.related_model = related_model
        self.remote_field_name = remote_field_name
        
    def get_related_url(self, info, action, *args):
        from django.urls import reverse
        return reverse("admin:%s_%s_%s" % (info + (action,)), args=args)
                       
    def get_context(self, name, value, attrs):
        from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
        rel_opts = self.related_model._meta
        info = (rel_opts.app_label, rel_opts.model_name)
        self.widget.choices = self.choices
        url_params = '&'.join("%s=%s" % param for param in [
            (TO_FIELD_VAR, self.remote_field_name),
            (IS_POPUP_VAR, 1),
        ])
        context = {
            'rendered_widget': self.widget.render(name, value, attrs),
            'name': name,
            'url_params': url_params,
            'model': rel_opts.verbose_name,
        }
        if self.can_change_related:
            change_related_template_url = self.get_related_url(info, 'change', '__fk__')
            context.update(
                can_change_related=True,
                change_related_template_url=change_related_template_url,
            )
        if self.can_add_related:
            add_related_url = self.get_related_url(info, 'add')
            context.update(
                can_add_related=True,
                add_related_url=add_related_url,
            )
        if self.can_delete_related:
            delete_related_template_url = self.get_related_url(info, 'delete', '__fk__')
            context.update(
                can_delete_related=True,
                delete_related_template_url=delete_related_template_url,
            )
        return context
        
def wrap_dal_widget(widget, remote_field_name = 'id'):
    # Using django.urls.resolve would result in a circular import when it tries to import MIZDB.urlconf (when trying to make BulkFormAusgabe)
    # we're coming from DBentry.forms -> MIZDB.urlconf -> DBentry.ie.urls -> DBentry.ie.views -> DBentry.ie.forms -> DBentry.forms
    # Accessing widget.url calls reverse() with the root conf for the app (MIZDB.urlconf), resulting in another circular import.
    # NOTE: resolve_lazy()???!
    from DBentry.ac.urls import autocomplete_patterns
    from django.urls import RegexURLResolver, NoReverseMatch
    from dal import autocomplete
    if not isinstance(widget, autocomplete.ModelSelect2) or not hasattr(widget, '_url'):
        return widget
    resolver = RegexURLResolver(r'', autocomplete_patterns)
    try:
        path = resolver.reverse(widget._url)
    except NoReverseMatch:
        # It is possible we were trying to wrap a widget with a 'nocreate' url
        # -- obviously we do not want to wrap this widget then
        return widget
    resolver_match = resolver.resolve(path)
    if resolver_match:
        match_view = resolver_match.func.view_class
        initkwargs = resolver_match.func.view_initkwargs
        related_model = match_view.model or initkwargs.get('model', None)
        if related_model:
            return EasyWidgetWrapper(widget, related_model, remote_field_name)
            
    return widget


    
def make_widget(url='accapture', multiple=False, wrap=False, remote_field_name='id', can_add_related=True, **kwargs):
    
    widget_attrs = {}
    model = kwargs.pop('model', None)
    model_name = kwargs.pop('model_name', '')
    if model and not model_name:
        model_name = model._meta.model_name
    if model_name and not model:
        model = get_model_from_string(model_name)
    
    if 'widget_class' in kwargs:
        widget_class = kwargs.pop('widget_class')
    else:
        if multiple:
            widget_class = MIZModelSelect2Multiple
        else:
            widget_class = MIZModelSelect2
        if model_name:
            widget_attrs['model_name'] = model_name
        else:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured("{} widget missing argument 'model_name'.".format(widget_class.__name__))
        if 'create_field' not in kwargs and can_add_related and model:
            kwargs['create_field'] = model.create_field
    if issubclass(widget_class, (autocomplete.ModelSelect2, autocomplete.ModelSelect2Multiple)):
        widget_attrs['url'] = url
        
    widget_attrs.update(kwargs)
    widget = widget_class(**widget_attrs)
        
    if wrap and remote_field_name:
        if model:
            return EasyWidgetWrapper(widget, model, remote_field_name)
    return widget
        
        
