import calendar
import datetime
from collections import OrderedDict
from typing import (
    Any, Dict, Iterable, List, Optional, OrderedDict as OrderedDictType, Sequence,
    Tuple, Union
)

from django.core.exceptions import FieldDoesNotExist
from django.core.validators import EMPTY_VALUES
from django.db import transaction
from django.db.models import Count, Max, Min, Model, QuerySet, OuterRef, Exists, Q
from django.db.models.constants import LOOKUP_SEP

from dbentry.fts.query import TextSearchQuerySetMixin
from dbentry.utils import leapdays


class MIZQuerySet(TextSearchQuerySetMixin, QuerySet):

    def values_dict(
            self,
            *fields: str,
            include_empty: bool = False,
            flatten: bool = False,
            **expressions: Any
    ) -> OrderedDictType[int, dict]:
        """
        An extension of QuerySet.values() that merges results for the same
        record.

        For example for  a pizza with two toppings and two sizes;

        values('pk', 'pizza__topping', 'pizza__size') will return:
                [
                    {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'Tiny'},
                    {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'Tiny'},
                    {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'God'},
                    {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'God'}
                ]


        values_dict('pk', 'pizza__topping', 'pizza__size') will return:
                {
                    1 : {
                        'pizza__topping' : ('Onions', 'Bacon' ),
                        'pizza__size': ('Tiny', 'God')
                    },
                }

        Args:
            *fields (str): list of field names/paths that should be included
            include_empty (bool): if True, include empty values as defined in
              django.core.validators.EMPTY_VALUES
            flatten (bool): if True, any values list that only contains one
              item will be replaced by just that item, removing the list. This
              does not apply to values from reverse related fields; in that
              case, an iterable is expected.
            **expressions: additional expressions for values()

        Returns:
            an OrderedDict of primary key to item values (dicts)
        """
        opts = self.model._meta
        # pk_name is the variable that will refer to this query's primary key
        # values.
        pk_name = opts.pk.name

        # Make sure the query includes the model's primary key values as we
        # require it to build the result out of.
        # If fields is empty, the query targets all the model's fields.
        if fields and pk_name not in fields:
            if 'pk' in fields:
                pk_name = 'pk'
            else:
                # The query does not query for the primary key at all;
                # it must be added to fields.
                fields += (pk_name,)

        # Do not flatten reverse relation values.
        # An iterable object is expected.
        flatten_exclude = []
        if flatten and fields:
            for field_path in fields:
                field_name = field_path
                if LOOKUP_SEP in field_path:
                    field_name = field_path.split(LOOKUP_SEP, 1)[0]
                try:
                    field = opts.get_field(field_name)
                except FieldDoesNotExist:
                    # Don't raise the exception here; let it be raised by
                    # self.values(). An invalid field will cause the query to
                    # fail anyway and django provides a much more detailed
                    # error message.
                    break
                if not field.concrete:
                    flatten_exclude.append(field_path)

        result: OrderedDictType[int, dict] = OrderedDict()
        for val_dict in self.values(*fields, **expressions):
            pk = val_dict.pop(pk_name)
            # For easier lookups of field_names, use dictionaries for the
            # item's values mapping.
            item_dict: Union[dict, tuple]  # for mypy
            if pk in result:
                # Multiple rows returned due to joins over relations for this
                # primary key.
                item_dict = dict(result[pk])
            else:
                item_dict = {}
            for field_path, value in val_dict.items():
                if not include_empty and value in EMPTY_VALUES:
                    continue
                values: tuple  # for mypy
                if field_path not in item_dict:
                    values = ()
                elif flatten and not isinstance(item_dict[field_path], tuple):
                    # This value has previously been flattened!
                    values = (item_dict[field_path],)
                else:
                    values = item_dict[field_path]
                if values and value in values:
                    continue
                values += (value,)
                if flatten and len(values) == 1 and field_path not in flatten_exclude:
                    values = values[0]
                item_dict[field_path] = values
            result[pk] = item_dict
        return result

    def overview(self, *annotations) -> 'MIZQuerySet':
        """Return a queryset that provides a comprehensive overview of the objects."""
        return self.model.overview(self, *annotations)


class CNQuerySet(MIZQuerySet):
    # TODO: shouldn't get() update the name just like filter?

    def bulk_create(self, objs: Iterable[Model], **kwargs: Any) -> List[Model]:
        # Set the _changed_flag on the objects to be created
        for obj in objs:
            obj._changed_flag = True
        return super().bulk_create(objs, **kwargs)

    def defer(self, *fields: str) -> MIZQuerySet:
        if '_name' not in fields:
            self._update_names()
        return super().defer(*fields)

    def filter(self, *args: Any, **kwargs: Any) -> MIZQuerySet:
        if any(k.startswith('_name') for k in kwargs):
            self._update_names()
        return super().filter(*args, **kwargs)

    def only(self, *fields: str) -> MIZQuerySet:
        if '_name' in fields:
            self._update_names()
        return super().only(*fields)

    def update(self, **kwargs: Any) -> int:
        # Assume that a name update will be required after this update.
        # If _changed_flag is not already part of the update, add it.
        if '_changed_flag' not in kwargs:
            kwargs['_changed_flag'] = True
        return super().update(**kwargs)
    update.alters_data = True  # type: ignore[attr-defined]

    def values(self, *fields: str, **expressions: Any) -> MIZQuerySet:
        if '_name' in fields:
            self._update_names()
        return super().values(*fields, **expressions)

    def values_list(self, *fields: str, **kwargs: Any) -> MIZQuerySet:
        if '_name' in fields:
            self._update_names()
        return super().values_list(*fields, **kwargs)

    def _update_names(self) -> None:
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
                        _name=new_name, _changed_flag=False
                    )
    _update_names.alters_data = True  # type: ignore[attr-defined]


def build_date(
        years: List[int],
        month_ordinals: List[int],
        day: int = 1
) -> Optional[datetime.date]:
    """
    Helper function for AusgabeQuerySet.increment_jahrgang to build a
    datetime.date instance out of lists of years and month ordinals.
    """
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
    return datetime.date(year=year, month=month, day=day)


class AusgabeQuerySet(CNQuerySet):
    chronologically_ordered = False

    def _chain(self, **kwargs: Any) -> 'AusgabeQuerySet':
        clone = super()._chain(**kwargs)
        clone.chronologically_ordered = self.chronologically_ordered
        return clone

    def order_by(self, *field_names: str) -> 'AusgabeQuerySet':
        # Any call to order_by is almost guaranteed to break the
        # chronological ordering.
        self.chronologically_ordered = False
        return super().order_by(*field_names)

    def update(self, **kwargs: Any) -> int:
        if self.chronologically_ordered:
            # Need to clear ordering for the update.
            # The queryset's order depends on values from annotations - but
            # update() clears all annotations: an update on an ordered
            # queryset will fail.
            return self.order_by().update(**kwargs)
        return super().update(**kwargs)

    def search(self, q: str, search_type: str = 'plain', ranked: bool = True) -> 'AusgabeQuerySet':
        # Always apply the chronological ordering to the search results.
        return super().search(q, ranked=False).chronological_order()

    def increment_jahrgang(self, start_obj: Model, start_jg: int = 1) -> Dict[int, List[int]]:
        """
        Alter the 'jahrgang' values using ``start_obj`` as starting point.

        Set the jahrgang (i.e. the volume) value for ``start_obj`` to ``start_jg``
        and then alter the jahrgang values of the other ausgabe objects in this
        queryset according to whether they temporally come before or after the
        jahrgang of ``start_obj``.
        The time/jahrgang difference of other objects to ``start_obj`` is
        calculated using either (partial) dates, 'num' or simply the year values
        of the other objects; depending on the available data and in that order.

        Returns:
            a dictionary that was used to update the jahrgang values;
              it maps jahrgang to list of ids.
        """
        # TODO: the return value isn't use anywhere
        start = start_obj or self.chronological_order().first()
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
                'monat__ordinal', flat=True
            )
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

    def chronological_order(self, *order_fields: str) -> 'AusgabeQuerySet':
        """Return this queryset chronologically ordered."""
        # TODO: check out nulls_first and nulls_last parameters of
        #   Expression.asc() and desc() (added in 1.11) to fix the nulls
        #   messing up the ordering.
        if self.chronologically_ordered:
            # Already ordered!
            return self

        opts = self.model._meta
        # A chronological order is (mostly) consistent ONLY within the
        # ausgabe_set of one particular magazin. If the queryset contains the
        # ausgaben of more than one magazin, we may end up replacing one 'poor'
        # ordering (the default one) with another poor, but more expensive
        # chronological one. In that case, return self with some form of
        # ordering instead.
        if self.only('magazin').distinct().values_list('magazin').count() != 1:
            # This condition is also True if self is an empty queryset.
            if order_fields:
                return self.order_by(*order_fields)
            if self.query.order_by:
                return self
            return self.order_by(*opts.ordering)

        default_ordering = ('magazin__magazin_name', 'jahr', 'jahrgang', 'sonderausgabe')
        ordering: List[str] = [*order_fields, *default_ordering]

        pk_name = opts.pk.name
        # Retrieve the first item in ordering that refers to the primary key,
        # so we can later append it to the final ordering.
        # It makes no sense to have the queryset be ordered primarily on the
        # primary key.
        try:
            pk_order_item = next(
                filter(
                    lambda i: i in ('pk', '-pk', pk_name, '-' + pk_name),
                    ordering
                )
            )
            ordering.remove(pk_order_item)
        except StopIteration:
            # No primary key in ordering, use a default.
            pk_order_item = '-%s' % pk_name

        # Determine if jahr should come before jahrgang in ordering.
        jj_values: List[Tuple[int, int]] = list(self.values_list('ausgabejahr__jahr', 'jahrgang'))
        # Remove empty values and unzip the 2-tuples into two lists.
        jahr_values: Sequence[int]
        jahrgang_values: Sequence[int]
        jahr_values, jahrgang_values = (list(filter(None, _list)) for _list in zip(*jj_values))
        if len(jahrgang_values) > len(jahr_values):
            # Prefer jahrgang over jahr.
            jahr_index = ordering.index('jahr')
            jahrgang_index = ordering.index('jahrgang')
            ordering[jahr_index] = 'jahrgang'
            ordering[jahrgang_index] = 'jahr'

        clone = self.annotate(
            num=Max('ausgabenum__num'),
            monat=Max('ausgabemonat__monat__ordinal'),
            lnum=Max('ausgabelnum__lnum'),
            jahr=Min('ausgabejahr__jahr')
        )
        # Find the best (annotated) fields to order against.
        # Sort the fields e_datum, lnum, monat and num by how often the objects
        # of the queryset have values in those fields.
        from dbentry.models import AusgabeLnum, AusgabeNum, AusgabeMonat
        counted = (
            self
            .annotate(
                has_lnum=Exists(AusgabeLnum.objects.filter(ausgabe=OuterRef("pk"))),
                has_monat=Exists(AusgabeMonat.objects.filter(ausgabe=OuterRef("pk"))),
                has_num=Exists(AusgabeNum.objects.filter(ausgabe=OuterRef("pk")))
            )
            .aggregate(
                e_datum__sum=Count('e_datum'),
                lnum__sum=Count('has_lnum', filter=Q(has_lnum=True)),
                monat__sum=Count('has_monat', filter=Q(has_monat=True)),
                num__sum=Count('has_num', filter=Q(has_num=True)),
            )
        )
        default_criteria_ordering = [
            'e_datum__sum', 'lnum__sum', 'monat__sum', 'num__sum']

        # Tuples are sorted lexicographically in ascending order:
        # sorted([(1, 'c'), (1, 'b'), (2, 'a')]) = [(1, 'b'), (1, 'c'), (2, 'a')]
        # Here, we want to order the sums (tpl[1]) in descending/reverse order
        # (hence the minus operand), and if any sums are equal, the order of
        # sum_names in the defaults decides.
        criteria = sorted(
            counted.items(),
            key=lambda itemtpl: (-itemtpl[1], default_criteria_ordering.index(itemtpl[0]))
        )
        result_ordering = [sum_name.split('__')[0] for sum_name, _sum in criteria]
        ordering.extend(result_ordering + [pk_order_item])

        clone = clone.order_by(*ordering)
        clone.chronologically_ordered = True
        return clone
