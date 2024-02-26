import calendar
import datetime


def leapdays(start: datetime.date, end: datetime.date) -> int:
    """
    Count leap days between date instances.

    calendar.leapdays only uses integer years to count leap days which can be
    inaccurate:
    If the start and end year are the same, the result is always 0
    due to the end argument being regarded as exclusive.
    If either year is a leap year, the number of leap days depends on the
    exact dates.
    """
    # (used in AusgabeQuerySet.increment_jahrgang)
    if start > end:
        start, end = end, start

    start_leap = end_leap = None
    if calendar.isleap(start.year):
        start_leap = datetime.date(start.year, 2, 29)
    if calendar.isleap(end.year):
        end_leap = datetime.date(end.year, 2, 29)

    if start.year == end.year:
        if start_leap and start <= start_leap <= end:
            # A leap day lies between start and end.
            return 1
        return 0

    total_leapdays = calendar.leapdays(start.year, end.year)
    if start_leap and start >= start_leap:
        # calendar.leapdays would count the leap day of the start year even
        # if the start date lies past the leap day.
        total_leapdays -= 1
    if end_leap and end >= end_leap:
        # calendar.leapdays counts the leap days UP to the end year;
        # if the end date lies past the leap day, we must include it.
        total_leapdays += 1
    return total_leapdays
