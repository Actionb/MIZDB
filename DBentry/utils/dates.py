import calendar
import datetime

from DBentry.utils.inspect import is_iterable

def leapdays(start, end):
    # calendar.leapdays ignores the leap day if start.year == end.year and start.year is a leap year
    # it also ignores the leapday if the end date is in a leap year and the date is passed the leap day
    if start > end:
        start, end = end, start

    start_leap = end_leap = None
    if calendar.isleap(start.year):
        start_leap = datetime.date(start.year, 2, 29)
    if calendar.isleap(end.year):
        end_leap = datetime.date(end.year, 2, 29)

    if start.year == end.year:
        if start_leap and start < start_leap and end >= start_leap:
            return 1
        return 0

    leapdays = calendar.leapdays(start.year, end.year) # end year is EXCLUSIVE 
    if start_leap and start >= start_leap:
        # calendar.leapdays would count the leap day of the start year even if the start date lies after the leap day
        leapdays -= 1
    if end_leap and end >= end_leap:
        # calendar.leapdays treats the end year exclusively, i.e. it counts the leap days UP to that year
        # if the end date lies after the leap day, we must include it
        leapdays += 1
    return leapdays

def build_date(years, month_ordinals, day = None):
    if not is_iterable(years):
        years = [years]
    if not is_iterable(month_ordinals):
        month_ordinals = [month_ordinals]

    # Filter out None values that may have been returned by a values_list call
    none_filter = lambda x: x is not None
    years = list(filter(none_filter,  years))
    month_ordinals = list(filter(none_filter, month_ordinals))

    if not (years and month_ordinals):
        # either years or month_ordinals is an empty sequence
        return
    year = min(years)
    month = min(month_ordinals)

    if len(month_ordinals) > 1:
        # If the ausgabe spans several months, use the last day of the first appropriate month
        # to chronologically order it after any ausgabe that appeared 'only' in that first month
        if len(years) > 1:
            # the ausgabe spans two years, assume the latest month for the e_datum
            month = max(month_ordinals)
        # Get the last day of the chosen month
        day = calendar.monthrange(year, month)[1]

    if day is None:
        day = 1

    return datetime.date(
        year = year, 
        month = month, 
        day = day, 
    )
