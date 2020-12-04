import calendar
import datetime
from itertools import chain
from collections import Counter, OrderedDict, namedtuple

from nameparser import HumanName

from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db import models, transaction
from django.db.models import Count, Min, Max
from django.db.models.constants import LOOKUP_SEP

from DBentry.query import (
    BaseSearchQuery, ValuesDictSearchQuery, PrimaryFieldsSearchQuery
)
from DBentry.utils import leapdays, is_iterable


class MIZQuerySet(models.QuerySet):

    def find(self, q, ordered=False, strat_class=None, **kwargs):
        """
        Return a list of instances that contain search term 'q'.

        Find any occurence of the search term 'q' in the queryset, depending
        on the search strategy used.
        By default, the order of the results depends on the search strategy.
        If 'ordered' is True, results will be ordered according to the order
        established in the queryset instead.
        """
        if strat_class:
            strat_class = strat_class
        # Use the most accurate strategy possible:
        elif getattr(self.model, 'name_field', False):
            strat_class = ValuesDictSearchQuery
        elif getattr(self.model, 'primary_search_fields', False):
            strat_class = PrimaryFieldsSearchQuery
        else:
            strat_class = BaseSearchQuery
        strat = strat_class(self, **kwargs)
        result, exact_match = strat.search(q, ordered)
        return result

    def duplicates(self, *fields):
        """
        Find records that share values in the given fields.

        Returns a list of 'Dupe' named tuples.
        'Dupe' has two attributes:
            - instances: a queryset of records that share some values
            - values: the values that are shared
        """
        Dupe = namedtuple('Dupe', ['instances', 'values'])

        queried = self.values_dict(*fields, tuplfy=True)
        # chain all the values in queried to be able to later count over them.
        all_values = list(chain(values for pk, values in queried.items()))
        rslt = []
        # Walk through the values, looking for non-empty values that appeared
        # more than once.
        for elem, count in Counter(all_values).items():
            if not elem or count < 2:
                # Do not compare empty with empty.
                continue
            # Find all the pks that match these values.
            pks = []
            for pk, values in queried.items():
                if values == elem:
                    pks.append(pk)
            instances = self.model.objects.filter(pk__in=pks)
            rslt.append(Dupe(instances, elem))
        return rslt

    def values_dict(self, *fields, include_empty=False, flatten=False,
            tuplfy=False, **expressions):
        """
        An extension of QuerySet.values() that merges the results.

        For a pizza with two toppings and two sizes:
        values('pk', 'pizza__topping', 'pizza__size'):
                [
                    {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'Tiny'},
                    {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'Tiny'},
                    {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'God'},
                    {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'God'},
                ]

        values_dict('pk','pizza__topping', 'pizza__size'):
                {
                    '1' : {
                        'pizza__topping' : ('Onions', 'Bacon' ),
                        'pizza__size': ('Tiny', 'God')
                    },
                }
        """
        # pk_name is the variable that will refer to this query's primary key
        # values.
        pk_name = self.model._meta.pk.name

        # Make sure the query includes the model's primary key values as we
        # require it to build the result out of.
        # If fields is empty, the query targets all the model's fields.
        if fields:
            if pk_name not in fields:
                if 'pk' in fields:
                    pk_name = 'pk'
                else:
                    # The query does not query for the primary key at all;
                    # it must be added to fields.
                    fields += (pk_name, )

        # Do not flatten reverse relation values. An iterable is expected.
        flatten_exclude = []
        if flatten and fields:
            for field_path in fields:
                field_name = field_path
                if LOOKUP_SEP in field_path:
                    field_name = field_path.split(LOOKUP_SEP, 1)[0]
                try:
                    field = self.model._meta.get_field(field_name)
                except FieldDoesNotExist:
                    # Don't raise the exception here; let it be raised by
                    # self.values(). An invalid field will cause the query to
                    # fail anyway and django provides a much more detailed
                    # error message.
                    break
                if not field.concrete:
                    flatten_exclude.append(field_path)

        rslt = OrderedDict()
        for val_dict in self.values(*fields, **expressions):
            pk = val_dict.pop(pk_name)
            # For easier lookups of field_names, use dictionaries for the
            # item's values mapping. If tuplfy == True, we turn the values
            # mapping back into a tuple before adding it to the result.
            if pk in rslt:
                # Multiple rows returned due to joins over relations for this
                # primary key.
                item_dict = dict(rslt.get(pk))
            else:
                item_dict = {}
            for field_path, value in val_dict.items():
                if not include_empty and value in EMPTY_VALUES:
                    continue
                if field_path not in item_dict:
                    values = ()
                elif flatten and not isinstance(item_dict.get(field_path), tuple):
                    # This value has previously been flattend!
                    values = (item_dict.get(field_path), )
                else:
                    values = item_dict.get(field_path)
                if values and value in values:
                    continue
                values += (value, )
                if flatten and len(values) == 1 and field_path not in flatten_exclude:
                    values = values[0]
                item_dict[field_path] = values
            if tuplfy:
                item_dict = tuple(item_dict.items())
            rslt[pk] = item_dict
        return rslt


class CNQuerySet(MIZQuerySet):

    def bulk_create(self, objs, batch_size=None):
        # Set the _changed_flag on the objects to be created
        for obj in objs:
            obj._changed_flag = True
        return super().bulk_create(objs, batch_size)

    def defer(self, *fields):
        if '_name' not in fields:
            self._update_names()
        return super().defer(*fields)

    def filter(self, *args, **kwargs):
        if any(k.startswith('_name') for k in kwargs):
            self._update_names()
        return super().filter(*args, **kwargs)

    def only(self, *fields):
        if '_name' in fields:
            self._update_names()
        return super().only(*fields)

    def update(self, **kwargs):
        # Assume that a name update will be required after this update.
        # If _changed_flag is not already part of the update, add it.
        if '_changed_flag' not in kwargs:
            kwargs['_changed_flag'] = True
        return super().update(**kwargs)
    update.alters_data = True

    def values(self, *fields, **expressions):
        if '_name' in fields:
            self._update_names()
        return super().values(*fields, **expressions)

    def values_list(self, *fields, **kwargs):
        if '_name' in fields:
            self._update_names()
        return super().values_list(*fields, **kwargs)

    def _update_names(self):
        """Update the names of rows where _changed_flag is True."""
        if self.query.can_filter() and self.filter(_changed_flag=True).exists():
            values = self.filter(
                _changed_flag=True
            ).values_dict(
                *self.model.name_composing_fields,
                include_empty=False,
                flatten=False
            )
            with transaction.atomic():
                for pk, val_dict in values.items():
                    new_name = self.model._get_name(**val_dict)
                    self.order_by().filter(pk=pk).update(
                        _name=new_name, _changed_flag=False)
    _update_names.alters_data = True


def build_date(years, month_ordinals, day=None):
    """
    Helper function for AusgabeQuerySet.increment_jahrgang to build a
    datetime.date instance out of lists of years and month ordinals.
    """
    if not is_iterable(years):
        years = [years]
    if not is_iterable(month_ordinals):
        month_ordinals = [month_ordinals]

    # Filter out None values that may have been returned by a values_list call.
    years = list(filter(None, years))
    month_ordinals = list(filter(None, month_ordinals))

    if not (years and month_ordinals):
        # Either years or month_ordinals is an empty sequence.
        return None
    year = min(years)
    month = min(month_ordinals)

    if len(month_ordinals) > 1:
        # If the ausgabe spans several months, use the last day of the first
        # 'appropriate' month to chronologically order it after any ausgabe that
        # appeared only in that first month.
        # An ausgabe released at the end of a year that also includes the next
        # year should use the last month of the previous year.
        if len(years) > 1:
            month = max(month_ordinals)
        # Get the last day of the chosen month.
        day = calendar.monthrange(year, month)[1]

    return datetime.date(year=year, month=month, day=day or 1)


class AusgabeQuerySet(CNQuerySet):

    chronologically_ordered = False

    def _chain(self, **kwargs):
        # QuerySet._chain() will update the clone's __dict__ with the kwargs
        # we give it. (in django1.11: QuerySet._clone() did this job)
        if 'chronologically_ordered' not in kwargs:
            kwargs['chronologically_ordered'] = self.chronologically_ordered
        return super()._chain(**kwargs)

    def order_by(self, *args, **kwargs):
        # Any call to order_by is almost guaranteed to break the
        # chronologic ordering.
        self.chronologically_ordered = False
        return super().order_by(*args, **kwargs)

    def update(self, *args, **kwargs):
        if self.chronologically_ordered:
            # Trying to update a chronologically ordered queryset seems to fail.
            # A FieldError is raised, complaining about a missing field. That
            # field should exist as an annotation but just doesn't.
            # Proper solution to this would be check the update kwargs for
            # expressions that require ordering and handle those separately
            # somehow - but considering that chronologic_order's days are almost
            # numbered, this is the quick and dirty way of fixing the problem:
            return self.order_by().update(*args, **kwargs)
        return super().update(*args, **kwargs)

    def find(self, q, ordered=True, **kwargs):
        # Insist on preserving the chronologic order over the order created
        # by the search query (exact, startswith, contains).
        return super().find(q, ordered=ordered, **kwargs)

    def increment_jahrgang(self, start_obj, start_jg=1):
        """
        Alter the 'jahrgang' values using 'start_obj' as anchor.

        Set the 'jahrgang' (i.e. the volume) value for 'start_obj' to 'start_jg'
        and then alter the jahrgang values of the other ausgabe objects in this
        queryset according to whether they lie temporally before or after the
        jahrgang of 'start_obj'.
        The time/jahrgang difference of other objects to 'start_obj' is
        calculated using either (partial) dates, 'num' or simply the year values
        of the other objects; depending on the available data and in that order.

        Returns a dictionary that was used to update the jahrgang values;
        it maps jahrgang to list of ids.
        """
        start = start_obj or self.chronologic_order().first()
        start_date = start.e_datum
        years = start.ausgabejahr_set.values_list('jahr', flat=True)
        if start_date:
            start_year = start_date.year
        elif years:
            start_year = min(years)
        else:
            start_year = None

        ids_seen = {start.pk}
        update_dict = {start_jg: [start.pk]}
        queryset = self.exclude(pk=start.pk)

        # Increment jahrgang using a (partial) date.
        if start_date is None:
            month_ordinals = start.ausgabemonat_set.values_list(
                'monat__ordinal', flat=True)
            start_date = build_date(years, month_ordinals)

        if start_date:
            val_dicts = queryset.values_dict(
                'e_datum', 'ausgabejahr__jahr', 'ausgabemonat__monat__ordinal',
                include_empty=False, flatten=False
            )
            for pk, val_dict in val_dicts.items():
                if 'e_datum' in val_dict:
                    obj_date = val_dict.get('e_datum')[-1]
                elif ('ausgabejahr__jahr' not in val_dict
                        or 'ausgabemonat__monat__ordinal' not in val_dict):
                    # Need both year and month to build a meaningful date.
                    continue
                else:
                    obj_date = build_date(
                        val_dict['ausgabejahr__jahr'],
                        val_dict['ausgabemonat__monat__ordinal']
                    )
                if obj_date < start_date:
                    # If the obj_date lies before start_date the obj_jg will
                    # always be start_jg - 1 plus the year difference between
                    # the two dates.
                    # If obj_date is equal to start_date except for the year
                    # (same day, same month, different year), then obj_date
                    # marks the exact BEGINNING of the obj_jg, thus we need to
                    # handle it inclusively (subtracting 1 from the day
                    # difference, thereby requiring 366 days difference).
                    days = (start_date - obj_date).days - leapdays(start_date, obj_date) - 1
                    obj_jg = start_jg - 1 - int(days / 365)
                else:
                    days = (obj_date - start_date).days - leapdays(start_date, obj_date)
                    obj_jg = start_jg + int(days / 365)
                if obj_jg not in update_dict:
                    update_dict[obj_jg] = []
                update_dict[obj_jg].append(pk)
                ids_seen.add(pk)

        # Increment jahrgang using the ausgabe's num.
        nums = start.ausgabenum_set.values_list('num', flat=True)
        if nums and start_year:
            queryset = queryset.exclude(pk__in=ids_seen)
            start_num = min(nums)
            val_dicts = queryset.values_dict(
                'ausgabenum__num', 'ausgabejahr__jahr',
                include_empty=False, flatten=False
            )
            for pk, val_dict in val_dicts.items():
                if ('ausgabenum__num' not in val_dict
                        or 'ausgabejahr__jahr' not in val_dict):
                    continue

                obj_year = min(val_dict['ausgabejahr__jahr'])
                obj_num = min(val_dict['ausgabenum__num'])
                if len(val_dict['ausgabejahr__jahr']) > 1:
                    # The ausgabe spans two years, choose the highest num
                    # number to order it at the end of the year.
                    obj_num = max(val_dict['ausgabenum__num'])

                if ((obj_num > start_num and obj_year == start_year)
                        or (obj_num < start_num and obj_year == start_year + 1)):
                    # The object was released either:
                    #   - after the start object and within the same year
                    #   - *numerically* before the start object but in the year
                    #       following the start year (i.e. temporally after).
                    # Either way it still belongs to the same volume as start.
                    update_dict[start_jg].append(pk)
                else:
                    obj_jg = start_jg + obj_year - start_year
                    if obj_num < start_num:
                        # The object was released in the 'previous' jahrgang.
                        obj_jg -= 1
                    if obj_jg not in update_dict:
                        update_dict[obj_jg] = []
                    update_dict[obj_jg].append(pk)
                ids_seen.add(pk)

        # Increment by year.
        if start_year:
            queryset = queryset.exclude(pk__in=ids_seen)
            val_dicts = queryset.values_dict(
                'ausgabejahr__jahr', include_empty=False, flatten=False
            )
            for pk, val_dict in val_dicts.items():
                if 'ausgabejahr__jahr' not in val_dict:
                    continue
                obj_jg = start_jg + min(val_dict['ausgabejahr__jahr']) - start_year
                if obj_jg not in update_dict:
                    update_dict[obj_jg] = []
                update_dict[obj_jg].append(pk)
                ids_seen.add(pk)

        with transaction.atomic():
            for jg, ids in update_dict.items():
                self.filter(pk__in=ids).update(jahrgang=jg)

        return update_dict

    def chronologic_order(self, *ordering):
        """Return this queryset chronologically ordered."""
        # TODO: check out nulls_first and nulls_last parameters of
        # Expression.asc() and desc() (added in 1.11) to fix the nulls messing
        # up the ordering.
        if self.chronologically_ordered:
            # Already ordered!
            return self

        # A chronologic order is (mostly) consistent ONLY within
        # the ausgabe_set of one particular magazin. If the queryset contains
        # the ausgaben of more than one magazin, we may end up replacing one
        # 'poor' ordering (the default one) with another poor, but more
        # expensive chronologic one. Return self with some form of ordering.
        if self.only('magazin').distinct().values_list('magazin').count() != 1:
            # This condition is also True if self is an empty queryset.
            if ordering:
                return self.order_by(*ordering)
            if self.query.order_by:
                return self
            return self.order_by(*self.model._meta.ordering)

        # FIXME: default_ordering orders by 'magazin' and not 'magazin_name'?
        default_ordering = ['magazin', 'jahr', 'jahrgang', 'sonderausgabe']
        if ordering:
            ordering = list(ordering)
            ordering.extend(default_ordering)
        else:
            ordering = default_ordering

        pk_name = self.model._meta.pk.name
        # Retrieve the first item in ordering that refers to the primary key,
        # so we can later append it to the final ordering.
        # It makes no sense to have the queryset be ordered primarily on the
        # primary key.
        try:
            filter_func = lambda i: i in ('pk', '-pk', pk_name, '-' + pk_name)
            pk_order_item = next(filter(filter_func, ordering))
            ordering.remove(pk_order_item)
        except StopIteration:
            # No primary key in ordering, use a default.
            pk_order_item = '-%s' % pk_name

        # Determine if jahr should come before jahrgang in ordering.
        jj_values = list(self.values_list('ausgabejahr', 'jahrgang'))
        # Remove empty values and unzip the 2-tuples into two lists.
        jahr_values, jahrgang_values = (
            list(filter(lambda x: x is not None, l)) for l in zip(*jj_values)
        )
        if len(jahrgang_values) > len(jahr_values):
            # Prefer jahrgang over jahr.
            jahr_index = ordering.index('jahr')
            jahrgang_index = ordering.index('jahrgang')
            ordering[jahr_index] = 'jahrgang'
            ordering[jahrgang_index] = 'jahr'

        # Find the best criteria to order with, which might be either:
        # num, lnum, monat or e_datum
        # Count the presence of the different criteria and sort them accordingly.
        # NOTE: tests succeed with or without distinct = True
        counted = self.aggregate(
            e_datum__sum=Count('e_datum', distinct=True),
            lnum__sum=Count('ausgabelnum', distinct=True),
            monat__sum=Count('ausgabemonat', distinct=True),
            num__sum=Count('ausgabenum', distinct=True),
        )
        default_criteria_ordering = [
            'e_datum__sum', 'lnum__sum', 'monat__sum', 'num__sum']

        # Tuples are sorted lexicographically in ascending order. If any item
        # of two tuples is the same, it goes on to the next item:
        # sorted([(1, 'c'), (1, 'b'), (2, 'a')]) = [(1,'b'), (1, 'c'), (2, 'a')]
        # In this case, we want to order the sums (tpl[1]) in descending, i.e.
        # reverse, order (hence the minus operand) and if any sums are equal,
        # the order of sum_names in the defaults decides.
        criteria = sorted(
            counted.items(),
            key=lambda itemtpl: (
                -itemtpl[1], default_criteria_ordering.index(itemtpl[0])
            )
        )
        result_ordering = [sum_name.split('__')[0] for sum_name, sum in criteria]
        ordering.extend(result_ordering + [pk_order_item])

        clone = self.annotate(
            num=Max('ausgabenum__num'),
            monat=Max('ausgabemonat__monat__ordinal'),
            lnum=Max('ausgabelnum__lnum'),
            jahr=Min('ausgabejahr__jahr')
        ).order_by(*ordering)
        clone.chronologically_ordered = True
        return clone


class HumanNameQuerySet(MIZQuerySet):
    """Extension of MIZQuerySet that enables searches for 'human names'."""

    def _parse_human_name(self, text):
        try:
            return str(HumanName(text))
        except:
            # TODO: find out which exceptions might be raised by HumanName()
            return text

    def find(self, q, **kwargs):
        # Parse 'q' through HumanName first to 'combine' the various ways one
        # could write a human name.
        # (f.ex. 'first name surname' or 'surname, first name')
        q = self._parse_human_name(q)
        return super().find(q, **kwargs)


class PeopleQuerySet(HumanNameQuerySet, CNQuerySet):
    """Queryset for models where the names of people are primary."""
    pass
