import re
from itertools import chain

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext


class BulkField(forms.CharField):
    """
    A CharField that extracts a list of values from the data given.

    Attributes:
        default_separator (str): the separator that separates values.
        allowed_space (bool): if True, spaces may also be used to separate values.
        allowed_special: a list of special characters that may appear in the field's data.
    """

    default_error_messages = {
        'invalid_format': 'Ungültig formatierte Angaben: %(invalid_values)s.',
    }

    separator_pattern = r'\s*,\s*'
    range_pattern = r'^(?P<start>\d+)\s*-{1}\s*(?P<end>\d+)$'  # TODO: ^\s* at the start?
    range_grouping_pattern =r'^(?P<start>\d+)\s*-{1}\s*(?P<end>\d+)\s*\*{1}\s*(?P<multi>\d+)$'
    grouping_pattern = r'^\d+(\s*\/{1}\s*\d+)+$'

    def __init__(self, required=False, *args, **kwargs):
        super().__init__(required=required,  *args, **kwargs)
        self.separator_regex = re.compile(self.separator_pattern)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        # Limit the width of the BulkField's widget to 350px.
        attrs['style'] = 'width:350px;'
        return attrs

    def get_regex_patterns(self):
        return [self.range_pattern, self.range_grouping_pattern, self.grouping_pattern]

    @property
    def regexes(self):
        if not hasattr(self, '_regexes'):
            self._regexes = list(map(re.compile, self.get_regex_patterns()))
        return self._regexes

    def run_regexes(self, value):
        for regex in self.regexes:
            match = regex.search(value)
            if match:
                return match

    def validate(self, value):
        """Validate that only allowed characters appear in 'value'."""  # TODO: adjust docstring
        super().validate(value)
        if not value:
            return

        invalid = []
        for item in self.separator_regex.split(value):
            if item.isnumeric():
                continue
            if not self.run_regexes(item):
                invalid.append(item)
        if invalid:
            raise ValidationError(
                self.error_messages['invalid_format'],
                params = {'invalid_values': ", ".join(invalid)},
                code = 'invalid_format'
            )

    def clean(self, value):
        if value:
            # Remove whitespaces and empty items.
            value = ",".join([
                item.replace(' ', '')
                for item in self.separator_regex.split(value)
                if item.strip()
            ])
        return super().clean(value)

    def to_list(self, value):
        """
        Split the value at commas (and spaces if allowed_space is True) into
        a list of values.

        If an item contains a '-' (indicating a range of values) or a 
        '/' (indicating a grouping of values) a sublist containing the subitems
        is added to the list.
        If an item contains a '-' and a '*' subitems will be grouped according
        to the numerical following the '*'.
        Examples (item: added to the result list):
            '10-13': [10, 11, 12 ,13]
            '10/11': [10,11]
            '10-13*2': [10, 11], [12, 13]

        Return that list of values and the total count of returned strings
        and sublists.
        """
        if not value:
            return [], 0
        temp = []
        item_count = 0  # FIXME: item_count is always len(temp) -- EXCEPT for BulkJahrField!
        
        for item in self.separator_regex.split(value):
            if item.isnumeric():
                temp.append(item)
                item_count += 1
                continue
            if '-' in item:
                match = self.run_regexes(item)
                if match is None:
                    continue
                start, end = map(int, match.groups()[:2])
                multi = int(match.groupdict().get('multi', 1))
                # Add each item (or grouping) as a separate list.
                for i in range(start, end+1, multi):
                    temp.append([str(i+j) for j in range(multi)])
                    item_count += 1
            elif '/' in item:
                # Item is a 'grouping' of values.
                temp.append([i.strip() for i in item.split('/') if i.strip()])
                item_count += 1
        return temp, item_count


class BulkJahrField(BulkField):

    # Treat the slash as a separator just like a comma.
#    separator_pattern = r'\/|,'

    def get_regex_patterns(self):
        return [self.grouping_pattern]

    def validate(self, value):
        super().validate(value)

        for item in self.separator_regex.split(value):
            for jahr in item.split('/'):
                if jahr and len(jahr) != 4:
                    raise ValidationError('Bitte vierstellige Jahresangaben benutzen.')

    def to_list(self, value):
        temp, item_count = super().to_list(value)
        return temp, 0
