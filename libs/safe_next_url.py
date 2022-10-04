from flask import request

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


def safe_next_url(relative_url):
    '''
    Ensure a relative URL path is on the same domain as this host
    
    This protects against the 'Open redirect vulnerability'

    Params:
        relative_url (str): Relative url (typically supplied by Flask-Login)

    Returns: 
        full_url (str):    Pre-fixes path with full-host URL 
    '''
    
    full_url = urljoin(request.host_url, relative_url)
    
    return full_url
