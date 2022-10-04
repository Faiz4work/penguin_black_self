import json
import ipinfo

def ip_to_region(ip_address, access_token):
    '''
    Finds which country an IP address originates from 
    
    Params:
        ip_address (str):     IP address to check 
        access_token (str):   ...
    
    Returns: 
        country (str): Corresponding country 
    '''
    
    handler = ipinfo.getHandler(access_token)
    
    # All fields
    details = handler.getDetails(ip_address).details
    
    # Extract country 
    country = details['country_name']
    
    return country
