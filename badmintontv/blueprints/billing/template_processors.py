import datetime
import pytz

from libs.money import cents_to_dollars


def format_currency(amount, convert_to_dollars=True):
    '''
    Pad currency with 2 decimals and commas, and optionally convert cents to dollars

    Params:
        amount (int or float):        Amount in cents or dollars
        convert_to_dollars (bool):    If True, convert cents to dollars; False otherwise 
    
    Returns: Formatted currency 
    '''
    
    if convert_to_dollars:
        amount = cents_to_dollars(amount)

    return '{:,.2f}'.format(amount)


def current_year():
    '''Returns: This year (int)'''
    return datetime.datetime.now(pytz.utc).year
