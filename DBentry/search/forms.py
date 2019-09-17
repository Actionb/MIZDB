# TODO: have 'and'/'or' checkboxes for SelectMultiple
from collections import OrderedDict

from django import forms
from django.core import exceptions
from django.db.models import lookups as django_lookups
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import QuerySet
from django.utils.datastructures import MultiValueDict

from DBentry.ac.widgets import make_widget
from DBentry.forms import MIZAdminFormMixin
from DBentry.search import utils as search_utils


class RangeWidget(forms.MultiWidget):
    """
    A MultiWidget that takes one widget and duplicates it for the purposes
    of __range lookups.
    """

    class Media:
        css = {
            'all': ('admin/css/rangewidget.css', )
        }
    template_name = 'rangewidget.html'

    def __init__(self, widget, attrs=None):
        super().__init__(widgets=[widget]*2, attrs=attrs)

    def decompress(self, value):  # TODO: docstring
        # What is value? Where does it come from?
        # Why is it okay to assume it's a string?
        # Why is it okay to assume it only contains one comma?
        # decompress is only called in get_context which is only used to
        # render the widget.
        if value:
            return value.split(',')
        return [None, None]


class RangeFormField(forms.MultiValueField):
    """
    A MultiValueField wrapper around a formfield that duplicates the field for
    use in a __range lookup (start, end).
    """

    widget = RangeWidget

    def __init__(self, formfield, require_all_fields=False, **kwargs):
        if not kwargs.get('widget'):
            kwargs['widget'] = RangeWidget(formfield.widget)
        self.empty_values = formfield.empty_values
        super().__init__(
            fields=[formfield]*2,
            require_all_fields=require_all_fields,
            **kwargs
        )

    def get_initial(self, initial, name):
        widget_data = self.widget.value_from_datadict(initial, None, name)
        if isinstance(self.fields[0], forms.MultiValueField):
            # The sub fields are MultiValueFields themselves,
            # let them figure out the correct values for the given data.
            return [
                self.fields[0].compress(widget_data[0]),
                self.fields[1].compress(widget_data[1])
            ]
        else:
            return widget_data

    def clean(self, value):
        """Delegate cleaning to the clean method of each field."""
        return [self.fields[0].clean(value[0]), self.fields[1].clean(value[1])]


class SearchForm(forms.Form):
    """
    Base form for the changelist search form.

    This form class is the default base class for searchform_factory.
    It adds the method 'get_filters_params' that transforms the form's cleaned
    data into valid queryset filter() keyword arguments.

    Attributes:
        - range_upper_bound: the lookup class that will be used when
            a 'start' value is not provided for a range lookup.
            defaults to: django.db.models.lookups.LessThanOrEqual
    The factory adds the following attribute:
        - lookups: mapping of formfield_name: list of valid lookups
    """

    range_upper_bound = django_lookups.LessThanOrEqual

    class Media:
        css = {
            'all': ('admin/css/forms.css', 'admin/css/search_form.css')
        }
        js = ['admin/js/remove_empty_fields.js', 'admin/js/collapse.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial = self.prepare_initial(self.initial)

# FIXME: get_initial_for_field and prepare_initial seem pointless:
# where is a search form initialized with initial data?
# The changelist view only passes 'data'.
    def get_initial_for_field(self, field, field_name):
        if (field_name not in self.initial and
                isinstance(field, forms.MultiValueField)):
            # Only the individual subfields show up in a request payload.
            if isinstance(field, RangeFormField):
                return field.get_initial(self.initial, field_name)
            widget_data = field.widget.value_from_datadict(
                data=self.initial, files=None, name=field_name
            )
            return field.compress(widget_data)
        return super().get_initial_for_field(field, field_name)

    def prepare_initial(self, initial):
        # initial may contain lists of values;
        # keep the lists with length > 1 (for SelectMultiple) but flatten all others
        cleaned = {}
        if isinstance(initial, MultiValueDict):
            iterator = initial.lists()
        else:
            iterator = initial.items()
        for k, v in iterator:
            if isinstance(v, (list, tuple)) and len(v) <= 1:
                cleaned[k] = v[0] if v else None
            else:
                cleaned[k] = v
        return cleaned

    def get_filters_params(self):
        """
        Return a dict of queryset filters based on the form's cleaned_data
        to filter the changelist with.
        Adds any field specific lookups and clears 'empty' values.
        """
        params = {}
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
                    param_key = field_name
                    param_value = start
                elif start_empty and not end_empty:
                    # no start but end: lte lookup for end
                    param_key = "".join(
                        [field_name, LOOKUP_SEP, self.range_upper_bound.lookup_name]
                    )
                    param_value = end
            elif (isinstance(formfield, forms.BooleanField) and
                    not isinstance(formfield, forms.NullBooleanField) and
                    not value):
                # value is False on a simple BooleanField;
                # don't include it in the filter parameters.
                continue
            elif (value in formfield.empty_values or
                    isinstance(value, QuerySet) and
                    not value.exists()):
                # Dont want empty values as filter parameters!
                continue

            params[param_key] = param_value
        return params


class MIZAdminSearchForm(MIZAdminFormMixin, SearchForm):
    """A search form that includes django media and supports fieldsets."""

    pass


class SearchFormFactory:
    """
    Helper object around the central method 'get_search_form' to facilitate
    building a form class for changelist filtering.
    """

    def __call__(self, *args, **kwargs):
        return self.get_search_form(*args, **kwargs)

    def get_default_lookup(self, formfield):
        """Return default lookups for a given formfield instance."""
        if isinstance(formfield.widget, forms.SelectMultiple):
            return ['in']
        return []

    def resolve_to_dbfield(self, model, field_path):
        """
        Follow the given 'field_path' from 'model' and return the final concrete
        model field along the path and the path's remainder (lookups).
        Raises FieldDoesNotExist if the field_path does not resolve to an
        existing model field.
        Raises FieldError if the field_path results in a reverse relation.
        """
        return search_utils.get_dbfield_from_path(model, field_path)

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Create a formfield for the given model field 'db_field' using the
        keyword arguments provided.
        If no widget is provided and the field is a relation, a dal widget
        will be created.
        """
        # It's a search form, nothing is required!
        # Also disable the help_texts.
        defaults = {'required': False, 'help_text': None}
        if db_field.is_relation and 'widget' not in kwargs:
            # Create a dal autocomplete widget:
            widget_opts = {
                'model': db_field.related_model, 'multiple': db_field.many_to_many,
                'wrap': False, 'can_add_related': False,
            }
            if kwargs.get('forward') is not None:
                widget_opts['forward'] = kwargs.pop('forward')
            defaults['widget'] = make_widget(**widget_opts)
        return db_field.formfield(**{**defaults, **kwargs})

    def get_search_form(
            self, model, fields=None, form=None, formfield_callback=None,
            widgets=None, localized_fields=None, labels=None, help_texts=None,
            error_messages=None, field_classes=None,
            forwards=None,
            range_lookup=django_lookups.Range,
            ):
        """
        Create and return a search form class for a given model.

        In regards to the creation of the formfields, this method works quite
        the same way as the method that creates the formfields for a ModelForm:
        django.forms.models.fields_for_model.
        Most arguments to get_search_form fulfill the same purposes as those
        to fields_for_model.
        One difference is that the collection 'fields' may contain field_paths
        to other models ('foo__bar') and/or lookups ('foo__contains').

        Any lookups that are valid lookups for the model field are stored in a
        mapping, called 'lookups', of formfield_name: lookups which is attached
        to resulting form class. This is done to allow lookups in admin that are
        not whitelisted as a list_filter (see: ModelAdmin.lookup_allowed).
        If the lookup (or parts of it) is a range lookup a RangeFormField is
        automatically created, wrapping the default formfield class for that
        formfield. If no lookups are included in the field_path, a default
        lookup will be retrieved from get_default_lookup().

        Additional arguments.
            - forwards: a mapping of formfield_name: dal forwards
            - range_lookup: the lookup class whose lookup_name is used to
                recognize range lookups.
        """
        if formfield_callback is None:
            formfield_callback = self.formfield_for_dbfield
        if not callable(formfield_callback):
            raise TypeError('formfield_callback must be a function or callable')

        # Create the formfields.
        attrs = OrderedDict()
        lookup_mapping = {}
        for path in (fields or []):
            try:
                db_field, lookups = self.resolve_to_dbfield(model, path)
                search_utils.validate_lookups(db_field, lookups)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError):
                # Either the field_path does not end a model field
                # or it ended in a reverse relation
                # or a lookup used was invalid.
                continue

            formfield_kwargs = {}
            if widgets and path in widgets:
                formfield_kwargs['widget'] = widgets[path]
            if (localized_fields == forms.models.ALL_FIELDS or
                    (localized_fields and path in localized_fields)):
                formfield_kwargs['localize'] = True
            if labels and path in labels:
                formfield_kwargs['label'] = labels[path]
            if help_texts and path in help_texts:
                formfield_kwargs['help_text'] = help_texts[path]
            if error_messages and path in error_messages:
                formfield_kwargs['error_messages'] = error_messages[path]
            if field_classes and path in field_classes:
                formfield_kwargs['form_class'] = field_classes[path]
            if forwards and path in forwards:
                formfield_kwargs['forward'] = forwards[path]
            # Use the path stripped of all lookups as the formfield's name.
            formfield_name = search_utils.strip_lookups_from_path(path, lookups)
            formfield = formfield_callback(db_field, **formfield_kwargs)
            if range_lookup.lookup_name in lookups:
                # A range lookup is used;
                # wrap the formfield in a RangeFormField.
                attrs[formfield_name] = RangeFormField(
                    formfield, required=False, **formfield_kwargs
                )
            else:
                attrs[formfield_name] = formfield
            # Add the lookups used to the lookup_mapping for this formfield.
            if not lookups:
                lookups = self.get_default_lookup(formfield)
            lookup_mapping[formfield_name] = lookups

        base_form = form or SearchForm
        attrs['lookups'] = lookup_mapping
        form_class_name = '%sSearchForm' % model._meta.model_name.capitalize()
        return type(form_class_name, (base_form, ), attrs)


searchform_factory = SearchFormFactory()
