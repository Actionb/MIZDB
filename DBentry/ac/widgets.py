from django.contrib.admin.widgets import RelatedFieldWidgetWrapper

class EasyWidgetWrapper(RelatedFieldWidgetWrapper):
    
    def __init__(self, widget, related_model, remote_field_name = 'id', can_add_related=True, can_change_related=True):
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        self.can_add_related = can_add_related
        self.can_change_related = can_change_related
        self.can_delete_related = False
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
