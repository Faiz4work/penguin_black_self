from flask import jsonify


def render_json(status, *args, **kwargs):
    '''
    Returns a JSON response 

    Example usage:
        render_json(404, {'error': 'Discount code not found.'})

    Params:
        status (int): HTTP status code
    
    Returns: Flask response
    '''
    response = jsonify(*args, **kwargs)
    response.status_code = status

    return response
