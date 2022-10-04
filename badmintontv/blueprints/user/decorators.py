from functools import wraps

from flask import flash, redirect
from flask_login import current_user


def anonymous_required(url='/settings'):
    '''
    Only allows a user to access a route if they're NOT logged in
    
    Redirect a user to a specified location if they are logged in 
    
    (Does the opposite of @login_required from Flask-Login)

    Params:
        url (str): URL to be redirected to, if invalid

    Returns: Function
    '''
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            
            # If user is logged-in, re-direct to `/settings`
            if current_user.is_authenticated:
                return redirect(url)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*roles):
    '''
    Does a user have permission to view this page?

    Params:
        *roles: 1 or more allowed roles
    
    Returns: Function
    '''
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            
            # If the current user's role is NOT in the list of roles, redirect them away to the home page
            if current_user.role not in roles:
                flash('You do not have permission to do that.', 'error')
                return redirect('/')

            return f(*args, **kwargs)
        return decorated_function
    return decorator
