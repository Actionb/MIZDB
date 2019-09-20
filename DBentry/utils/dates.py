import calendar
import datetime


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

