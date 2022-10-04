from wtforms.validators import ValidationError

from badmintontv.blueprints.user.models import User


def ensure_existing_password_matches(form, field):
    '''
    Ensure that the current password matches their existing password

    Params:
        form:          `wtforms` Instance
        field (str):   Field being passed in
    '''
    
    # Get user by ID 
    user = User.query.get(form._obj.id)

    # Raise error if can't authenticate with password 
    if not user.authenticated(password=field.data):
        raise ValidationError('Does not match.')


def ensure_identity_exists(form, field):
    '''
    Ensure an identity exists

    Params:
        form:          `wtforms` Instance
        field (str):   Field being passed in
    '''
    
    # Get user by identity 
    user = User.find_by_identity(field.data)

    # Raise error if user can't be found 
    if not user:
        raise ValidationError('Unable to locate account.')
