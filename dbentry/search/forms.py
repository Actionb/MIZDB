from collections import OrderedDict
from typing import Any, List, Optional, Type, Union

from django import forms
from django.core import exceptions
from django.db.models import Field, Model, lookups as django_lookups
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import QuerySet

from dbentry.admin.autocomplete.widgets import make_widget as make_dal_widget
from dbentry.admin.forms import MIZAdminFormMixin
from dbentry.autocomplete.widgets import make_widget as make_mizselect_widget
from dbentry.fields import PartialDate
from dbentry.search import utils as search_utils


class RangeWidget(forms.MultiWidget):
    """
    A MultiWidget that takes one widget and duplicates it for the purposes
    of __range lookups.
    """

    class Media:
        css = {
            'all': ('mizdb/css/rangewidget.css',)
        }

    template_name = 'rangewidget.html'

    def __init__(self, widget: forms.Widget, attrs: Optional[dict] = None) -> None:
        super().__init__(widgets=[widget] * 2, attrs=attrs)

    def decompress(self, value: Optional[str]) -> Union[List[str], List[None]]:
        # Split value into two values (start, end).
        # NOTE:
        # decompress is only used to prepare single values fetched from the
        # database, either for use as initial values or as data if the field
        # is disabled (see MultiValueField methods has_changed and clean).
        # But RangeWidget is only used in search forms and only interacts with
        # data put in by the user, and never database data, so this method is
        # never called.
        if value and isinstance(value, str) and value.count(',') == 1:
            return value.split(',')
        return [None, None]


class RangeFormField(forms.MultiValueField):
    """
    A MultiValueField wrapper around a formfield that duplicates the field for
    use in a __range lookup (start, end).
    """

    widget = RangeWidget

    def __init__(
            self,
            formfield: forms.Field,
            require_all_fields: bool = False,
            **kwargs: Any
    ) -> None:
        if not kwargs.get('widget'):
            # Create a RangeWidget from the formfield's default widget.
            kwargs['widget'] = RangeWidget(formfield.widget)
        self.empty_values = formfield.empty_values
        super().__init__(
            fields=[formfield] * 2,
            require_all_fields=require_all_fields,
            **kwargs
        )

    def get_initial(self, initial: dict, name: Any) -> list:
        # noinspection PyArgumentList
        widget_data = self.widget.value_from_datadict(data=initial, files=None, name=name)
        if isinstance(self.fields[0], forms.MultiValueField):
            # The subfields are also MultiValueFields; let them figure out the
            # correct values for the given data.
            return [
                self.fields[0].compress(widget_data[0]),
                self.fields[1].compress(widget_data[1])
            ]
        else:
            return widget_data

    def compress(self, data_list: list) -> list:
        if not data_list:
            # Return two empty values, one for each field.
            return [None, None]
        return data_list


class SearchForm(forms.Form):
    """
    Base form for the changelist search forms and the default form class for the
    search form factory.

    This form class adds the method ``get_filters_params`` that transforms the
    form's cleaned data into valid queryset filter() keyword arguments.

    Attributes:
        - ``lookups``: a mapping of {formfield_name: field lookups} that
          contains valid lookups for a given formfield.
          This mapping is filled by the search form factory.
        - ``range_upper_bound``: the lookup class that will be used when
          a 'start' value is not provided for a range lookup.
          defaults to: django.db.models.lookups.LessThanOrEqual
    """
    lookups: dict
    range_upper_bound = django_lookups.LessThanOrEqual

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.lookups = getattr(self, 'lookups', None) or {}

    @property
    def media(self) -> forms.Media:
        return super().media + forms.Media(js=['search/js/remove_empty_fields.js'])

    def get_filters_params(self) -> dict:
        """
        Return a dict of queryset filters based on the form's cleaned_data
        to filter the changelist with.
        Adds any field specific lookups and clears 'empty' values.
        """
        params: dict = {}
        if not self.is_valid():
            return params

        for field_name, value in self.cleaned_data.items():
            formfield = self.fields[field_name]
            if self.lookups.get(field_name, False):
                param_key = "%s__%s" % (
                    field_name, LOOKUP_SEP.join(self.lookups[field_name])
                )
            else:
                param_key = field_name
            param_value = value

            if isinstance(formfield, RangeFormField):
                start, end = value
                start_empty = start in formfield.empty_values
                end_empty = end in formfield.empty_values
                if start_empty and end_empty:
                    # start and end are empty: just skip it.
                    continue
                elif not start_empty and end_empty:
                    # start but no end: exact lookup for start
                    if isinstance(start, PartialDate):
                        # Just a single partial date: use contains lookup.
                        param_key = f"{field_name}__contains"
                    else:
                        param_key = field_name
                    param_value = start
                elif start_empty and not end_empty:
                    # no start but end: lte lookup for end
                    param_key = "".join(
                        [field_name, LOOKUP_SEP, self.range_upper_bound.lookup_name]
                    )
                    param_value = end
            elif (isinstance(formfield, forms.BooleanField)
                  and not isinstance(formfield, forms.NullBooleanField)
                  and not value):
                # value is False on a simple BooleanField;
                # don't include it in the filter parameters.
                continue
            elif (value in formfield.empty_values
                  or isinstance(value, QuerySet)
                  and not value.exists()):
                # Don't want empty values as filter parameters!
                continue
            elif ('in' in self.lookups.get(field_name, [])
                  and isinstance(value, QuerySet)):
                # django admin prepare_lookup_value expects a single string
                # of comma separated values for this lookup.
                param_value = ",".join(
                    str(pk) for pk in value.values_list('pk', flat=True).order_by('pk')
                )

            params[param_key] = param_value
        return params

    def clean_id__in(self) -> str:
        """Clean the ID value by Removing any non-numeric characters."""
        # Use case: the 'Plakat ID' is presented with a prefixed 'P'.
        # People will try to query for the id WITH that prefix.
        return "".join(
            i for i in self.cleaned_data.get('id__in', '') if i.isnumeric() or i == ','
        )


class MIZAdminSearchForm(MIZAdminFormMixin, SearchForm):
    """A search form that includes django media and supports fieldsets."""

    @property
    def media(self) -> forms.Media:
        css = {'all': ('admin/css/forms.css', 'admin/css/search_form.css')}
        js = ['search/js/remove_empty_fields.js', 'admin/js/collapse.js']
        return super().media + forms.Media(css=css, js=js)


class SearchFormFactory:
    """
    Helper object around the central method ``get_search_form`` to facilitate
    building a form class for changelist filtering.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Type[SearchForm]:
        return self.get_search_form(*args, **kwargs)

    def get_default_lookup(self, formfield: forms.Field) -> Union[List[str], list]:
        """Return default lookups for a given formfield instance."""
        if isinstance(formfield.widget, forms.SelectMultiple):
            return ['in']
        return []

    def get_widget(self, db_field: Field, path: str, **kwargs: Any) -> Optional[forms.Widget]:
        """
        Hook for setting default widgets for the form fields of a model field.

        Args:
            db_field (model field): the model field of the form field
            path (str): the field path for the model field as declared in the
              search form's fields argument. Use it to extract arguments specific
              to the current field from the kwargs.
            **kwargs (dict): additional keyword arguments passed through from
              the get_search_form call
        """
        return None

    def get_formfield(
            self,
            db_field: Field,
            formfield_class: Optional[forms.Field] = None,
            **kwargs: Any
    ) -> forms.Field:
        """
        Create a form field for the model field `db_field`.

        Args:
            db_field: the model field of the formfield
            formfield_class: the class of the formfield
            kwargs: formfield keyword arguments passed in from the search form
              factory call
        """
        defaults = {
            'required': False,  # It's a search form, nothing is required!
            'help_text': None  # Also disable the help_texts
        }
        if db_field.choices and not db_field.blank:
            # Always include an 'empty' choice in the choices, since 'required'
            # is always False.
            defaults['choices'] = db_field.get_choices(include_blank=True)
        if formfield_class:
            defaults['form_class'] = formfield_class
        defaults.update(kwargs)
        formfield = db_field.formfield(**defaults)
        if formfield is None:
            # AutoField.formfield() returns None; create a CharField as a
            # fallback.
            return forms.CharField(**defaults)
        return formfield

    def get_search_form(
            self,
            model: Type[Model],
            fields: Optional[list[str]] = None,
            form: Optional[Type[forms.Form]] = None,
            widgets: Optional[dict[str, forms.Widget]] = None,
            localized_fields: Optional[list[str]] = None,
            labels: Optional[dict[str, str]] = None,
            help_texts: Optional[dict[str, str]] = None,
            error_messages: Optional[dict[str, dict[str, str]]] = None,
            field_classes: Optional[dict[str, Type[forms.Field]]] = None,
            range_lookup: Type[django_lookups.Range] = django_lookups.Range,
            **kwargs: Any
    ) -> Type[SearchForm]:
        """
        Create and return a search form class for a given model.

        Any lookups specified in a field path in ``fields`` that are valid
        lookups for the model field are stored on the resulting form class in a
        dictionary called 'lookups'. This is done to allow lookups in admin that
        are not whitelisted as a list_filter (see: ModelAdmin.lookup_allowed).
        If the lookup (or parts of it) is a range lookup, a RangeFormField is
        automatically created, wrapping the default formfield class for that
        formfield. If no lookups are included in the field path, a default
        lookup will be retrieved from get_default_lookup().

        Args:
            model: the model to create the form for
            fields: a list of field names or paths to use in the form. These
              names/paths may include lookups.
            form: the base form class for the search form
            widgets: a dictionary of model field names mapped to a widget
            localized_fields: list of names of fields which should be localized
            labels: a dictionary of model field names mapped to a label
            help_texts: a dictionary of model field names mapped to a help text
            error_messages: a dictionary of model field names mapped to a
              dictionary of error messages
            field_classes: a dictionary of model field names mapped to a form
              field class
            range_lookup: the lookup class whose lookup_name is used for range
              lookups
            kwargs: additional arguments passed to the get_widget method
        """
        opts = model._meta
        # Create the formfields.
        attrs = OrderedDict()
        lookup_mapping = {}
        includes_pk = False  # True if 'fields' included the primary key of this model.
        for path in (fields or []):
            try:
                db_field, lookups = search_utils.get_dbfield_from_path(model, path)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError):
                continue
            if opts.pk == db_field:
                includes_pk = True

            formfield_kwargs = {}
            if widgets and path in widgets:
                formfield_kwargs['widget'] = widgets[path]
            else:
                formfield_kwargs['widget'] = self.get_widget(db_field, path, **kwargs)
            if (localized_fields == forms.models.ALL_FIELDS
                    or (localized_fields and path in localized_fields)):
                formfield_kwargs['localize'] = True
            if labels and path in labels:
                formfield_kwargs['label'] = labels[path]
            if help_texts and path in help_texts:
                formfield_kwargs['help_text'] = help_texts[path]
            if error_messages and path in error_messages:
                formfield_kwargs['error_messages'] = error_messages[path]

            formfield_class = None
            if field_classes and path in field_classes:
                formfield_class = field_classes[path]
            formfield = self.get_formfield(db_field, formfield_class=formfield_class, **formfield_kwargs)

            # Use the path stripped of all lookups as the formfield's name.
            formfield_name = search_utils.strip_lookups_from_path(path, lookups)
            if range_lookup.lookup_name in lookups:
                # Wrap the formfield in a RangeFormField for this range lookup:
                attrs[formfield_name] = RangeFormField(
                    formfield, required=False, **formfield_kwargs
                )
            else:
                attrs[formfield_name] = formfield
            # Add the lookups used to the lookup_mapping for this formfield.
            if not lookups:
                lookups = self.get_default_lookup(formfield)
            lookup_mapping[formfield_name] = lookups
        if not includes_pk:
            # A search field for the primary key was not included;
            # add a basic formfield.
            # By including the lookup in the field name data (instead of
            # registering it separately in the lookup_mapping), the name meshes
            # with the query string created by utils.get_changelist_url
            # (which uses 'id__in').
            db_field = opts.pk
            if db_field.is_relation and db_field.remote_field.parent_link:
                # Create a search field for the parent's primary key field
                # instead of the relation (that would produce some kind of
                # select field).
                db_field = db_field.target_field
            attrs['id__in'] = self.get_formfield(db_field, label='ID')

        base_form = form or SearchForm
        attrs['lookups'] = lookup_mapping  # type: ignore[assignment]
        form_class_name = '%sSearchForm' % opts.model_name.capitalize()
        # noinspection PyTypeChecker
        return type(form_class_name, (base_form,), attrs)


class DALSearchFormFactory(SearchFormFactory):
    """
    A search form factory that uses django-autocomplete-light (DAL) widgets for
    relation fields.
    """

    def get_widget(
            self,
            db_field: Field,
            path: str,
            tabular: Optional[list[str]] = None,
            forwards: Optional[dict[str, str]] = None,
            **kwargs: Any
    ) -> forms.Widget:
        """Create a dal widget if the field is a relation field."""
        if not db_field.is_relation:
            return super().get_widget(db_field, path)
        widget_opts = {
            'model': db_field.related_model,
            'multiple': db_field.many_to_many,
            'wrap': False,
            'can_add_related': False,
            'tabular': bool(tabular and path in tabular),
        }
        if forwards and path in forwards:
            widget_opts['forward'] = forwards[path]
        return make_dal_widget(**widget_opts)


class MIZSelectSearchFormFactory(SearchFormFactory):
    """
    A search form factory that uses MIZSelect autocomplete widgets for
    relation fields.
    """

    def get_widget(
            self,
            db_field: Field,
            path: str,
            tabular: Optional[list[str]] = None,
            filter_by: Optional[dict[str, str]] = None,
            **kwargs: Any
    ) -> forms.Widget:
        """Create a MIZSelect if the field is a relation field."""
        if not db_field.is_relation:
            return super().get_widget(db_field, path)
        widget_opts = {
            'model': db_field.related_model,
            'multiple': db_field.many_to_many,
            'can_add': False,
            'can_edit': False,
            'tabular': bool(tabular and path in tabular),
        }
        if filter_by and path in filter_by:
            widget_opts['filter_by'] = filter_by[path]
        return make_mizselect_widget(**widget_opts)
