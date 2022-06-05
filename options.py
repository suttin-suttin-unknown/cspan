import time
from enum import Enum
from datetime import datetime, timedelta


class TransactionRangeOptions(Enum):
    DAY = 0
    WEEK = 1
    MONTH = 2
    YEAR = 3
    DAY_START = 4
    WEEK_START = 5
    MONTH_START = 6
    YEAR_START = 7


def get_unix_time_from_timestamp(timestamp):
    return round(time.mktime(timestamp.timetuple()))


def get_timestamp_for_range(option, fromdate=datetime.utcnow()):
    if option == TransactionRangeOptions.DAY:
        timestamp = fromdate - timedelta(days=1)
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.WEEK:
        timestamp = fromdate - timedelta(days=7)
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.MONTH:
        timestamp = fromdate - timedelta(days=30)
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.YEAR:
        timestamp = fromdate - timedelta(days=365)
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.DAY_START:
        delta = timedelta(hours=fromdate.hour, 
            minutes=fromdate.minute, 
            seconds=fromdate.second, 
            microseconds=fromdate.microsecond)
        timestamp = fromdate - delta
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.WEEK_START:
        delta = timedelta(days=fromdate.weekday(), 
            hours=fromdate.hour, 
            minutes=fromdate.minute, 
            seconds=fromdate.second, 
            microseconds=fromdate.microsecond)
        timestamp = fromdate - delta
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.MONTH_START:
        days = max(fromdate.day - 1, 0)
        delta = timedelta(days=days, 
            hours=fromdate.hour, 
            minutes=fromdate.minute,
            seconds=fromdate.second, 
            microseconds=fromdate.microsecond)
        timestamp = fromdate - delta
        return get_unix_time_from_timestamp(timestamp)

    elif option == TransactionRangeOptions.YEAR_START:
        timestamp = datetime(fromdate.year, 1, 1)
        return get_unix_time_from_timestamp(timestamp)

    else:
        raise Exception("Invalid option.")
