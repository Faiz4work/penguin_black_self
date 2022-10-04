import stripe

from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def subscription_required(f):
    '''
    Ensure a user is subscribed, if not redirect them to the pricing table

    Returns: Function
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        if not current_user.subscription:
            return redirect(url_for('billing.pricing'))

        return f(*args, **kwargs)
    return decorated_function


def video_lock(f):
    '''
    Locks the video player page, if not redirect them to the pricing table

    Returns: Function
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        if not current_user.is_authenticated or not (current_user.subscription or current_user.role == 'admin'):
            return redirect(url_for('billing.pricing'))

        return f(*args, **kwargs)
    return decorated_function


def handle_stripe_exceptions(f):
    '''
    Handle Stripe exceptions so they do not throw 500s errors back to the user

    Params:
        f: Function
        
    Returns: Function
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        try:
            return f(*args, **kwargs)
        
        # ...
        except stripe.error.CardError:
            flash('Sorry, your card was declined. Try again perhaps?', 'error')
            return redirect(url_for('user.settings'))
        
        # ...
        except stripe.error.InvalidRequestError as e:
            flash(e, 'error')
            return redirect(url_for('user.settings'))
            
        # Handles incorrect API keys 
        except stripe.error.AuthenticationError:
            flash('Authentication with our payment gateway failed.', 'error')
            return redirect(url_for('user.settings'))
        
        # Handles Stripe's servers having connection issues 
        except stripe.error.APIConnectionError:
            flash('Our payment gateway is experiencing connectivity issues, please try again.', 'error')
            return redirect(url_for('user.settings'))
            
        # ...
        except stripe.error.StripeError:
            flash('Our payment gateway is having issues, please try again.', 'error')
            return redirect(url_for('user.settings'))

    return decorated_function
