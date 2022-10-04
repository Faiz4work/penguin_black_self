from flask_wtf import Form


class ModelForm(Form):
    '''
    `wtforms_components` exposes `ModelForm` but their verion of it does not inherit
    from `flask_wtf`'s Form, but instead `WTForm`'s Form

    However, in order to get CSRF protection handled by default we need to
    inherit from `flask_wtf`'s Form. So let's just copy its class directly

    We modified it by removing the format argument so that `wtforms_component`
    uses its own default which is to pass in `request.form` automatically
    '''
    def __init__(self, obj=None, prefix='', **kwargs):
        Form.__init__(
            self, obj=obj, prefix=prefix, **kwargs
        )
        self._obj = obj


def choices_from_dict(source, prepend_blank=True):
    '''
    Converts a dict to a format that's compatible with WTForm's choices
    It also optionally prepends a "Please select one..." value

    Example:
    
        # Convert this data structure:
        STATUS = OrderedDict([
          ('unread', 'Unread'),
          ('open', 'Open'),
          ('contacted', 'Contacted'),
          ('closed', 'Closed')
        ])

        # Into this:
        choices = [
            ('', 'Please select one...'), 
            ('unread', 'Unread'),
            ...
        ]
        
        # Note: This makes it so that in a form, the following will be shown:
        - (optional) 'Please select one...'
        - 'Unread'
        - ...

    Params:
        source (dict):          Input source
        prepend_blank (bool):   An optional blank item
    
    Returns:
        choices (list):    List of choices 
    '''
    choices = []

    if prepend_blank:
        choices.append(('', 'Please select one...'))

    for key, value in source.items():
        pair = (key, value)
        choices.append(pair)

    return choices


# Unused 
def choices_from_list(source, prepend_blank=True):
    '''
    Convert a list to a format that's compatible with WTForm's choices. It also
    optionally prepends a "Please select one..." value.

    Example:
        # Convert this data structure:
        TIMEZONES = (
            'Africa/Abidjan',
            'Africa/Accra',
            'Africa/Addis_Ababa'
        )

        # Into this:
        choices = [
            ('', 'Please select one...'),
            ('Africa/Abidjan', 'Africa/Abidjan),
            ...
        ]

    source (list or tuple):  Input source
    prepend_blank (bool):    An optional blank item

    Returns:
        choices (list):    List of choices 
    '''
    choices = []

    if prepend_blank:
        choices.append(('', 'Please select one...'))

    for item in source:
        pair = (item, item)
        choices.append(pair)

    return choices
