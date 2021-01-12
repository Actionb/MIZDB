from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from dbentry import models as _models
from dbentry.ac.widgets import make_widget
from dbentry.base.forms import MIZAdminForm, MinMaxRequiredFormMixin
from dbentry.constants import ATTRS_TEXTAREA, DUPLETTEN_ID, ZRAUM_ID
from dbentry.bulk.fields import BulkField, BulkJahrField, BaseSplitField


class BulkForm(MIZAdminForm):
    """
    Base form to facilitate bulk creation of model instances.

    All formfields must either be in 'each_fields' or 'split_fields' if their
    values are meant to contribute to model instances.
    Attributes:
        model: the model class of the instances to be created.
        each_fields: a sequence of formfield names whose values will be added
            to every instance created.
        split_fields: a sequence of names of BaseSplitField formfield instances
            whose values will be split up to serve as base data for each
            different instance. All field values in split_fields must contain
            the same amount of 'items'.
    """

    model = None
    each_fields = ()
    split_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._row_data = []
        each_fieldset = (
            'Angaben dieser Felder werden jedem Datensatz zugewiesen',
            {'fields': [
                field_name
                for field_name in self.fields if field_name in self.each_fields
            ]}
        )
        split_fieldset = (
            'Angaben dieser Felder werden aufgeteilt',
            {'fields': [
                field_name
                for field_name in self.fields if field_name in self.split_fields
            ]}
        )
        self.fieldsets = [each_fieldset, split_fieldset, (None, {'fields': []})]

    @property
    def row_data(self):
        """
        Prepare data for each instance.

        BulkAusgabe view uses this property to build the rows for preview table.
        """
        return self._row_data

    def has_changed(self):
        """Return True if data differs from initial and reset _row_data."""
        has_changed = bool(self.changed_data)
        if has_changed:
            # Reset _row_data.
            self._row_data = []
        return has_changed

    def clean(self):
        """
        Populate self.split_data with data from BaseSplitFields.to_list and
        establish the total number of 'items' (instances) to be created.

        split_data is a dictionary of:
            {field names: split up values according to BulkField.to_list}
        It is later used to create the row_data.

        Raises a field error if a field returns a differing amount of 'items'.
        """
        cleaned_data = super().clean()
        if self._errors:
            # Other cleaning methods have added errors, stop further cleaning.
            return cleaned_data

        self.total_count = 0
        self.split_data = {}
        for fld_name, fld in self.fields.items():
            if not isinstance(fld, BaseSplitField):
                continue
            # Retrieve the split up data and the amount of objects that are
            # expected to be created with that data.
            list_data, item_count = fld.to_list(cleaned_data.get(fld_name))
            # If the field belongs to the each_fields group, we should
            # ignore the item_count it is returning as its data is used for
            # every object we are about to create.
            if (fld_name not in self.each_fields
                    and item_count
                    and self.total_count
                    and item_count != self.total_count):
                # This field's data exists and is meant to be split up into
                # individual items, but the amount of items differs from
                # the previously determined total_count.
                self.add_error(
                    field=fld_name,
                    error='Ungleiche Anzahl an {}.'.format(
                        self.model._meta.verbose_name_plural
                    )
                )
            else:
                # Either:
                # - the field is an each_field
                # - its item_count is zero
                # - no total_count has yet been determined (meaning this is
                #   the first field encountered that contains list_data)
                if list_data:
                    self.split_data[fld_name] = list_data
                if item_count and fld_name not in self.each_fields:
                    # The item_count is not zero, total_count IS zero
                    # (not yet calculated) and the field is eligible
                    # (by virtue of being a non-each_fields SplitField) to
                    # set the total_count. All subsequent SplitField's
                    # item_counts in the iteration have to match this field's
                    # item_count (or be zero) or we cannot define the exact
                    # number of objects to create.
                    self.total_count = item_count
        return cleaned_data


class BulkFormAusgabe(MinMaxRequiredFormMixin, BulkForm):
    """The BulkForm to bulk create instances for model 'ausgabe' with."""

    # BulkForm attributes:
    model = _models.Ausgabe
    each_fields = [
        'magazin', 'jahrgang', 'jahr', 'audio', 'audio_lagerort',
        'ausgabe_lagerort', 'dublette', 'provenienz', 'beschreibung',
        'bemerkungen', 'status'
    ]
    split_fields = ['num', 'monat', 'lnum']

    # MinMaxRequiredFormMixin attributes:
    minmax_required = [
        {'min': 1, 'fields': ['jahr', 'jahrgang']},
        {'min': 1, 'fields': ['num', 'monat', 'lnum']}
    ]
    field_order = [
        'magazin', 'jahrgang', 'jahr', 'status', 'beschreibung', 'bemerkungen',
        'audio', 'audio_lagerort', 'ausgabe_lagerort', 'dublette', 'provenienz'
    ]

    # Field declarations:
    magazin = forms.ModelChoiceField(
        required=True,
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(model_name='magazin', wrap=True)
    )
    jahrgang = forms.IntegerField(required=False, min_value=1)
    jahr = BulkJahrField(required=False, label='Jahr')
    num = BulkField(label='Nummer')
    monat = BulkField(label='Monate')
    lnum = BulkField(label='Laufende Nummer')
    audio = forms.BooleanField(required=False, label='Musik Beilage:')
    audio_lagerort = forms.ModelChoiceField(
        required=False,
        queryset=_models.Lagerort.objects.all(),
        widget=make_widget(model_name='lagerort', wrap=True),
        label='Lagerort f. Musik Beilage'
    )
    ausgabe_lagerort = forms.ModelChoiceField(
        required=True,
        queryset=_models.Lagerort.objects.all(),
        widget=make_widget(model_name='lagerort', wrap=True),
        initial=ZRAUM_ID,
        label='Lagerort f. Ausgaben'
    )
    dublette = forms.ModelChoiceField(
        required=True,
        queryset=_models.Lagerort.objects.all(),
        widget=make_widget(model_name='lagerort', wrap=True),
        initial=DUPLETTEN_ID,
        label='Lagerort f. Dubletten'
    )
    provenienz = forms.ModelChoiceField(
        required=False,
        queryset=_models.Provenienz.objects.all(),
        widget=make_widget(model_name='provenienz', wrap=True)
    )
    beschreibung = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs=ATTRS_TEXTAREA),
        label='Beschreibung'
    )
    bemerkungen = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs=ATTRS_TEXTAREA),
        label='Bemerkungen'
    )
    status = forms.ChoiceField(
        choices=_models.Ausgabe.STATUS_CHOICES,
        initial=1,
        label='Bearbeitungsstatus'
    )

    def clean(self):
        # If the user wishes to add audio data to the objects they are creating,
        # they MUST also define a lagerort for the audio.
        if (self.cleaned_data.get('audio')
                and not self.cleaned_data.get('audio_lagerort')):
            self.add_error(
                field='audio_lagerort',
                error='Bitte einen Lagerort für die Musik Beilage angeben.'
            )
        return super().clean()

    def clean_monat(self):
        # Complain about monat values that are not in the valid range of 1-12.
        value = self.fields['monat'].widget.value_from_datadict(
            self.data, self.files, self.add_prefix('monat')
        )
        list_data, _ = self.fields['monat'].to_list(value)
        for item in list_data.copy():
            # item is either a string (a single month ordinal)
            # or a list of strings (a group of month ordinals).
            if not isinstance(item, list):
                item = [item]
            if any(int(month) < 1 or int(month) > 12 for month in item):
                raise ValidationError(
                    message='Monat-Werte müssen zwischen 1 und 12 liegen.',
                    code='invalid_month'
                )
        return value

    def lookup_instance(self, row):
        """
        For given data of a row, apply queryset filtering to find a matching
        instance.

        Returns a queryset instance with the results.
        """
        qs = self.cleaned_data.get('magazin').ausgabe_set.all()
        # Check the queryset before adding joins.
        # Return it as is if there is less or equal than one instance found.
        if qs.count() <= 1:
            return qs

        for fld_name, field_path in [
                ('num', 'ausgabenum__num'),
                ('lnum', 'ausgabelnum__lnum'),
                ('monat', 'ausgabemonat__monat__ordinal')]:
            row_data = row.get(fld_name, [])
            if isinstance(row_data, str):
                row_data = [row_data]
            for value in row_data:
                if value:
                    qs = qs.filter(**{field_path: value})

        jg = row.get('jahrgang', None)
        jahre = row.get('jahr', None)
        if isinstance(jahre, str):
            jahre = [jahre]
        if jg and jahre:
            if qs.filter(jahrgang=jg, ausgabejahr__jahr__in=jahre).exists():
                qs = qs.filter(jahrgang=jg, ausgabejahr__jahr__in=jahre)
            else:
                # Do not shadow possible duplicates that
                # only have one of (jg, jahre) by using OR.
                qs = qs.filter(
                    Q(('jahrgang', jg)) | Q(('ausgabejahr__jahr__in', jahre))
                )
        elif jg:
            qs = qs.filter(jahrgang=jg)
        elif jahre:
            qs = qs.filter(ausgabejahr__jahr__in=jahre)
        return qs.distinct()

    @property
    def row_data(self):
        """Prepare data for each instance."""
        if not self.is_valid():
            return []
        if not self.has_changed() and self._row_data:
            # Only (re)calculate if the form has changed or _row_data is empty.
            return self._row_data
        # Form is valid: split_data and total_count have been
        # computed in clean().
        for c in range(self.total_count):
            row = {}
            for field_name, _formfield in self.fields.items():
                if field_name not in self.each_fields + self.split_fields:
                    # This field was not assigned to either each_fields or
                    # split_fields: ignore it.
                    continue
                if field_name in self.split_data:
                    if field_name in self.each_fields:
                        # All items of this list are part of this row.
                        item = self.split_data.get(field_name)
                    else:
                        # Only one item of this list needs to be part of this row.
                        item = self.split_data.get(field_name)[c]
                else:
                    item = self.cleaned_data.get(field_name)
                if item:
                    row[field_name] = item

            # Check for duplicate rows and and assign the right lagerort to
            # this instance.
            qs = self.lookup_instance(row)
            row['ausgabe_lagerort'] = self.cleaned_data['ausgabe_lagerort']
            if qs.count() == 0:
                # No ausgabe fits the parameters: we are creating a new one.
                # See if this row (in its exact form) has already appeared
                # in _row_data. We do not want to create multiple
                # objects with the same data, instead we will mark this
                # row as a duplicate of the first matching row found.
                # By checking for row == row_dict we
                # avoid 'nesting' duplicates.
                for row_dict in self._row_data:
                    if row == row_dict:
                        row['ausgabe_lagerort'] = self.cleaned_data['dublette']
                        row['dupe_of'] = row_dict
                        break
            elif qs.count() == 1:
                # A single object fitting the parameters already exists:
                # this row represents a duplicate of that object.
                row['instance'] = qs.first()
                row['ausgabe_lagerort'] = self.cleaned_data['dublette']
            else:
                # lookup_instance returned multiple instances/objects:
                # this row will be ignored from now on.
                row['multiples'] = qs

            self._row_data.append(row)
        return self._row_data
