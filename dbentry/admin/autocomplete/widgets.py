from typing import Any, Optional, Tuple, Type

# noinspection PyPackageRequirements
from dal import autocomplete, forward
from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models import Model
from django.forms import Media, Widget
from django.urls import reverse

from dbentry.utils.models import get_model_from_string
from dbentry.utils.text import snake_case_to_spaces

# Generic URL-name for the MIZWidgetMixin.
GENERIC_URL_NAME = 'acgeneric'

# Name of the key under which views.ACTabular will add additional data for
# (grouped) result items.
EXTRA_DATA_KEY = 'extra_data'


class GenericURLWidgetMixin(object):
    """
    A mixin for autocomplete.ModelSelect2 widgets that works on a generic
    url name.

    The work flow for (dal) autocomplete widgets is:
        1. create view
        2. map view to URL (and url name)
        3. add widget using that URL (or url name) to a form field
        4. widget is used and an ajax request is made to that URL
        5. view responds with the results for the widget to display

    A downside is, that this requires having a URL for every different model
    that one would like to use ModelSelect2 on.
    To avoid explicitly declaring a URL for every model, a generic URL with a
    captured model name can be used: ``path('<str:model_name>/', name='generic')``.

    By passing the model name to the widget, the widget can then reverse that
    generic URL - and pass the specific URL (f.ex. 'foo/' for model 'foo')
    on to the template.

    Attributes:
        generic_url_name (str): if set, and if it matches the url name provided
          in the widget arguments, the widget will reverse that url name with
          arguments from _get_reverse_kwargs(). generic_url_name will replace a
          default url parameter (i.e. an empty string) and (in that case) will
          be passed to the super class constructor as keyword argument 'url'.
    """

    generic_url_name: str = ''

    # noinspection PyShadowingNames
    def __init__(
            self,
            model_name: str,
            url: Optional[str] = '',
            forward: Optional[list] = None,
            *args: Any,
            **kwargs: Any
    ) -> None:
        self.model_name = model_name
        if url == '':  # allow for explicit url=None
            url = self.generic_url_name
        super().__init__(url, forward, *args, **kwargs)  # type: ignore[call-arg]

    def _get_reverse_kwargs(self, **kwargs: Any) -> dict:
        """Return the kwargs required for reversing the widget's url name."""
        if self.model_name:
            return {'model_name': self.model_name, **kwargs}
        return kwargs

    def _get_url(self) -> Optional[str]:
        if self._url is None:
            return None

        if '/' in self._url:
            return self._url

        if self._url == self.generic_url_name:
            return reverse(self._url, kwargs=self._get_reverse_kwargs())

        return reverse(self._url)

    def _set_url(self, url: Optional[str]) -> None:
        self._url = url

    url = property(_get_url, _set_url)


class MIZWidgetMixin(GenericURLWidgetMixin):
    """
    A mixin for the ModelSelect2 widgets that enables the widget to handle
    reversal of the generic url name which requires reverse kwargs
    ``model_name`` and (sometimes) ``create_field``.
    """

    generic_url_name = GENERIC_URL_NAME

    def __init__(self, *args: Any, create_field: str = '', **kwargs: Any) -> None:
        self.create_field = create_field
        super().__init__(*args, **kwargs)

    def _get_reverse_kwargs(self, **kwargs: Any) -> dict:
        # Add create_field to the reverse kwargs:
        _kwargs = {}
        if self.create_field:
            _kwargs = {'create_field': self.create_field, **kwargs}
        else:
            _kwargs = kwargs
        return super()._get_reverse_kwargs(**_kwargs)


class TabularResultsMixin(object):
    """
    Widget mixin that uses a different autocomplete function to display results
    in a table.
    """

    autocomplete_function = 'select2Tabular'
    tabular_css_class = 'select2-tabular'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        attrs = self.attrs  # type: ignore[attr-defined]
        if 'class' in attrs and attrs['class']:
            attrs['class'] += ' ' + self.tabular_css_class
        else:
            attrs['class'] = self.tabular_css_class
        attrs['data-extra-data-key'] = EXTRA_DATA_KEY

    @property
    def media(self) -> Media:
        return super().media + Media(js=['admin/js/select2_tabular.js'])  # type: ignore[misc]


class MIZModelSelect2(MIZWidgetMixin, autocomplete.ModelSelect2):
    pass


class MIZModelSelect2Multiple(MIZWidgetMixin, autocomplete.ModelSelect2Multiple):
    pass


class MIZModelSelect2Tabular(TabularResultsMixin, MIZModelSelect2):
    pass


class MIZModelSelect2MultipleTabular(TabularResultsMixin, MIZModelSelect2Multiple):
    pass


class RemoteModelWidgetWrapper(RelatedFieldWidgetWrapper):
    """
    Wrapper that adds icons to perform add/change/delete on the widget's model.

    Unlike the super class RelatedFieldWidgetWrapper, this wrapper does not
    require a relation object. Instead, it 'addresses' the model that the
    widget is querying directly. This way one can add the add icons to any
    widget that manage a remote model - and not just the ones that manage a
    relation or a related field. (hence the class names)
    """

    @property
    def media(self) -> Media:
        """Add RelatedObjectLookups.js to the widget media."""
        # RelatedObjectLookups.js is added by ModelAdmin.media. In order to
        # wrap widgets for use in non-admin views, the wrapper needs to provide
        # the necessary javascript files directly.
        from django.conf import settings
        extra = '' if settings.DEBUG else '.min'
        js = [
            'admin/js/vendor/jquery/jquery%s.js' % extra,
            'admin/js/jquery.init.js',
            'admin/js/admin/RelatedObjectLookups.js'
        ]
        return Media(js=js) + super().media

    # noinspection PyMissingConstructor
    def __init__(
            self,
            widget: Widget,
            remote_model: Type[Model],
            remote_field_name: str = '',
            can_add_related: bool = True,
            can_change_related: bool = True,
            can_delete_related: bool = True
    ) -> None:
        """
        Instantiate the wrapper.

        Args:
            widget (Widget): the widget instance to wrap
            remote_model (model class): the model that the widget refers to
            remote_field_name (str): name of the field with which instances of
              the model can be uniquely identified. The value here will be
              added to the context as TO_FIELD_VAR, which is used throughout
              django admin and defaults to the primary key (opts.pk.attname)
            can_add_related (bool): if True, add a 'add' icon
            can_change_related (bool): if True, add a 'change' icon
            can_delete_related (bool): if True, add a 'delete' icon
        """
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        # noinspection PyUnresolvedReferences
        self.choices = widget.choices
        self.widget = widget
        multiple = getattr(widget, 'allow_multiple_selected', False)
        self.can_add_related = not multiple and can_add_related
        self.can_change_related = not multiple and can_change_related
        self.can_delete_related = not multiple and can_delete_related
        self.remote_model = remote_model
        # noinspection PyUnresolvedReferences
        self.remote_field_name = remote_field_name or remote_model._meta.pk.attname

    def get_related_url(self, info: Tuple[str, str], action: str, *args: Any) -> str:
        """
        Get the URL to the add/change/delete page of a related model.

        Args:
            info (2-tuple): the app label and model name of the related model
            action (str): the intended action on the related model
                (i.e. add/change/delete)
            *args: additional arguments to reverse()
        """
        # noinspection PyStringFormat
        return reverse("admin:%s_%s_%s" % (*info, action), args=args)

    def get_context(self, name: str, value: Any, attrs: dict) -> dict:
        # noinspection PyUnresolvedReferences
        rel_opts = self.remote_model._meta
        info = (rel_opts.app_label, rel_opts.model_name)
        self.widget.choices = self.choices
        url_params = '&'.join(
            "%s=%s" % param for param in [
                (TO_FIELD_VAR, self.remote_field_name),
                (IS_POPUP_VAR, 1),
            ]
        )
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
        url: str = GENERIC_URL_NAME,
        tabular: bool = False,
        multiple: bool = False,
        wrap: bool = False,
        remote_field_name: str = 'id',
        can_add_related: bool = True,
        can_change_related: bool = True,
        can_delete_related: bool = True,
        **kwargs: Any
) -> Widget:
    """
    Factory function that creates autocomplete widgets.

    Args:
        url: name of the url to the autocomplete view employed by this widget
        tabular (bool): if True, use the widget class that presents the results
          in tabular form
        multiple (bool): if True, a SelectMultiple variant will be used
        wrap (bool): if True, the widget will be wrapped with RemoteModelWidgetWrapper
        remote_field_name (str): wrapper arg: target of the relation field
        can_add_related (bool): wrapper arg: if True, add a 'add' icon
        can_change_related (bool): wrapper arg: if True, add a 'change' icon
        can_delete_related (bool): wrapper arg: if True, add a 'delete' icon
        kwargs: additional keyword arguments for the widget class constructor

    Raises:
        django.core.exceptions.ImproperlyConfigured: no model_name was provided,
          which is a required argument for widgets using GenericURLWidgetMixin
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
            if tabular:
                widget_class = MIZModelSelect2MultipleTabular
            else:
                widget_class = MIZModelSelect2Multiple
        else:
            if tabular:
                widget_class = MIZModelSelect2Tabular
            else:
                widget_class = MIZModelSelect2
        if model_name:
            widget_opts['model_name'] = model_name
        else:
            raise ImproperlyConfigured(
                "{} widget missing argument 'model_name'.".format(
                    widget_class.__name__
                )
            )
        if 'create_field' not in kwargs and can_add_related and model:
            widget_opts['create_field'] = model.create_field

    if issubclass(
            widget_class,
            (autocomplete.ModelSelect2, autocomplete.ModelSelect2Multiple)
    ):
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
            attrs = widget_opts.get('attrs', {})
            if 'attrs' not in widget_opts:
                widget_opts['attrs'] = attrs

            if 'data-placeholder' not in attrs:
                # forward with no data-placeholder-text
                placeholder_template = "Bitte zuerst %(verbose_name)s auswählen."

                # Try to find the verbose_name to of the source formfield
                # of the forward.
                # We do not have access to the form and so no access to the
                # forwarded formfield's (forwarded.src) label.
                # If the forward's dst attribute is None, then get_field is
                # likely to fail as src refers to the formfield's name
                # and not the model field's name.
                try:
                    # Reminder: a field's verbose_name defaults to:
                    #   field.name.replace('_',' ')

                    forwarded_verbose = model._meta.get_field(
                        forwarded.dst or forwarded.src
                    ).verbose_name.title()
                except (AttributeError, FieldDoesNotExist):
                    # AttributeError: the field returned by get_field does not
                    # have a verbose_name attribute (i.e. a relation)
                    # FieldDoesNotExist: forwarded.dst/forwarded.src is not
                    # a name of a field of that model
                    forwarded_verbose = snake_case_to_spaces(forwarded.src).title()
                placeholder = placeholder_template % {
                    'verbose_name': forwarded_verbose
                }
                attrs['data-placeholder'] = placeholder

    widget = widget_class(**widget_opts)

    if model and wrap and remote_field_name:
        return RemoteModelWidgetWrapper(
            widget, model, remote_field_name,
            can_add_related, can_change_related, can_delete_related
        )
    return widget
