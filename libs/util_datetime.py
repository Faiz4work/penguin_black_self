import datetime
import pytz
import calendar


def tzware_datetime():
    '''Returns an aware `datetime` object for right now'''
    return datetime.datetime.now(pytz.utc)


def datetime_to_utc_timestamp(dt):
    '''Converts an unaware `datetime` object --> UTC `int` timestamp'''
    return calendar.timegm(dt.utctimetuple())


def utc_timestamp_to_datetime(utc):
    '''Converts a UTC `int` timestamp --> unaware `datetime` object'''
    return datetime.datetime.utcfromtimestamp(utc)


def localize_datetime(unaware_dt):
    '''
    Converts an unaware `datetime` object --> aware UTC `datetime` object
    
    eg.
        Before:  2022-07-16 11:18:08 <class 'datetime.datetime'> 
        After:   2022-07-16 11:18:08+00:00 <class 'datetime.datetime'> 
    '''
    aware_dt = pytz.utc.localize(unaware_dt)
    return aware_dt


def format_datetime(dt, format='%b %d %Y, %H:%M:%S %p'):
    '''
    Format a `datetime` to make it more readable 
    
    eg. 
        Jul 17 2023, 11:18:24 AM
    
    Params:
        dt (datetime):   Datetime to format
        format (str):    New format
    '''
    return datetime.datetime.strftime(dt, format)


def timedelta_months(months, compare_date=None):
    '''
    Return a new datetime with a month offset applied

    Eg. `months=2` and `compare_date='May 2016'`` will return 'July 2016', 
        since that's `months` after `compare_date`        

    Params:
        param months (int):    Number of months to offset
        compare_date (date):   Date to compare at
    
    Returns: A `datetime` with a new threshold 
    '''
    
    if compare_date is None:
        compare_date = datetime.date.today()

    delta = months * 365 / 12
    compare_date_with_delta = compare_date + datetime.timedelta(delta)

    return compare_date_with_delta
