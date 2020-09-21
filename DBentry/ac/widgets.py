from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.urls import reverse

from dal import autocomplete, forward

from DBentry.utils import get_model_from_string, snake_case_to_spaces


class WidgetCaptureMixin(object):
    """
    A mixin for the ModelSelect2 widgets that enables the widget to handle
    reversal of the generic url name 'accapture' which requires reverse kwargs
    'model_name' and 'create_field'.
    """

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
        if self._url == 'accapture':
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
    """
    A class that wraps a given widget to add add/change/delete links and icons.

    Unlike its base class RelatedFieldWidgetWrapper, which is used during the
    creation of an AdminForm's formfields (BaseModelAdmin.formfield_for_dbfield),
    this wrapper is used during widget declaration of formfields of a form
    class.
    """

    @property
    def media(self):
        from django.conf import settings
        from django import forms
        extra = '' if settings.DEBUG else '.min'
        js = [
            'admin/js/vendor/jquery/jquery%s.js' % extra,
            'admin/js/jquery.init.js',
            'admin/js/admin/RelatedObjectLookups.js'
        ]
        return forms.Media(js=js) + super().media 

    def __init__(
            self, widget, related_model, remote_field_name='id',
            can_add_related=True, can_change_related=True,
            can_delete_related=True):
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.widget = widget
        multiple = getattr(widget, 'allow_multiple_selected', False)
        self.can_add_related = not multiple and can_add_related
        self.can_change_related = not multiple and can_change_related
        self.can_delete_related = not multiple and can_delete_related
        self.related_model = related_model
        self.remote_field_name = remote_field_name

    def get_related_url(self, info, action, *args):
        return reverse("admin:%s_%s_%s" % (info + (action,)), args=args)

    def get_context(self, name, value, attrs):
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
            url = self.get_related_url(info, 'change', '__fk__')
            context.update(
                can_change_related=True,
                change_related_template_url=url,
            )
        if self.can_add_related:
            url = self.get_related_url(info, 'add')
            context.update(
                can_add_related=True,
                add_related_url=url,
            )
        if self.can_delete_related:
            url = self.get_related_url(info, 'delete', '__fk__')
            context.update(
                can_delete_related=True,
                delete_related_template_url=url,
            )
        return context


def make_widget(
        url='accapture', multiple=False, wrap=False, remote_field_name='id',
        can_add_related=True, can_change_related=True, can_delete_related=True,
        **kwargs):
    """
    Factory function that creates autocomplete widgets.

    Arguments:
        - url: name of the url to the autocomplete view employed by this widget
        - multiple (boolean): if True, a SelectMultiple variant will be used
        - wrap (boolean): if True, the widget will be wrapped (using
            EasyWidgetWrapper) to add icons (add/change/delete related) to the
            admin interface.
        - remote_field_name: parameters for the EasyWidgetWrapper
        - can_x_related (boolean): parameters for the EasyWidgetWrapper

    Any other keyword arguments are passed on to the widget class constructor.
    """
    widget_opts = {}
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
            widget_opts['model_name'] = model_name
        else:
            raise ImproperlyConfigured(
                "{} widget missing argument 'model_name'.".format(
                    widget_class.__name__)
            )
        if 'create_field' not in kwargs and can_add_related and model:
            widget_opts['create_field'] = model.create_field

    if issubclass(
            widget_class,
            (autocomplete.ModelSelect2, autocomplete.ModelSelect2Multiple)):
        widget_opts['url'] = url

    widget_opts.update(kwargs)

    if 'forward' in widget_opts:
        _forward = widget_opts.get('forward')
        if not isinstance(_forward, (list, tuple)):
            _forward = [_forward]
        else:
            _forward = list(_forward)
        widget_opts['forward'] = []

        for forwarded in _forward:
            if not forwarded:
                continue
            if isinstance(forwarded, str):
                dst = forwarded.split('__')[-1]
                forwarded = forward.Field(src=forwarded, dst=dst)
            widget_opts['forward'].append(forwarded)

            if 'attrs' in widget_opts:
                attrs = widget_opts.get('attrs')
            else:
                widget_opts['attrs'] = {}
                attrs = widget_opts['attrs']

            if 'data-placeholder' not in attrs:
                # forward with no data-placeholder-text
                # the widget is created when django initializes, not when
                # the view is called apparently that is too early
                # for translations...
                # TODO: maybe this is fixed in DAL 3.2.10 (#871)?
                placeholder_template = "Bitte zuerst %(verbose_name)s auswählen."

                # Try to find the verbose_name of the source formfield
                # of the forward.
                # We do not have access to the form and so no access to the
                # forwarded formfield's (forwarded.src) label.
                # If the forward's dst attribute is None, then get_field is
                # likely to fail as src refers to the formfield's name
                # and not the model field's name.
                try:
                    # verbose_name default is the field.name.replace('_',' ')
                    forwarded_verbose = model._meta.get_field(
                        forwarded.dst or forwarded.src).verbose_name.title()
                except (AttributeError, FieldDoesNotExist):
                    # AttributeError: the field returned by get_field does not
                    # have a verbose_name attribute (i.e. a relation)
                    # FieldDoesNotExist: forwarded.dst/forwarded.src is not
                    # a name of a field of that model
                    forwarded_verbose = snake_case_to_spaces(forwarded.src).title()
                placeholder = placeholder_template % {
                    'verbose_name': forwarded_verbose}
                attrs['data-placeholder'] = placeholder

    widget = widget_class(**widget_opts)

    if model and wrap and remote_field_name:
        return EasyWidgetWrapper(
            widget, model, remote_field_name,
            can_add_related, can_change_related, can_delete_related
        )
    return widget
