from flask_wtf import Form
from wtforms import HiddenField, StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp
from wtforms_components import EmailField, Email, Unique

from config.settings import LANGUAGES
from libs.util_wtforms import ModelForm, choices_from_dict
from badmintontv.blueprints.user.models import User, db
from badmintontv.blueprints.user.validations import ensure_identity_exists, ensure_existing_password_matches


class BeginSignupForm(ModelForm):
    
    username = StringField(
        'Username',
        validators=[
            Unique(User.username, get_session=lambda: db.session),   # Must be unique 
            DataRequired(),
            Length(5, 30),
            # Part of the Python 3.7.x update included updating flake8 which means
            # we need to explicitly define our regex pattern with r'xxx'
            Regexp(r'^\w+$', message='Letters, numbers and underscores only please.')
        ]
    )
    
    email = EmailField(
        'Email',
        validators=[
            DataRequired(),
            Email(),            # Make sure it's in email format 
            Length(5, 255),
            Unique(User.email, get_session=lambda: db.session)   # Must be unique 
        ]
    )
    
    password = PasswordField(
        'Password', 
        validators=[
            DataRequired(), 
            Length(8, 128)
        ]
    )
    

class SignupForm(Form):
    
    # Used to make sure serialized token matches
    signup_token = HiddenField()


class LoginForm(Form):
    
    # Keeps track of where the user wanted to go originally, if they were re-directed to a URL with this form
    # After they log-in, they'll be automatically sent there
    next = HiddenField()
    
    # Users can log-in via username OR email
    identity = StringField(
        'Username or Email',
        validators=[
            DataRequired(), 
            Length(5, 255)
        ]
    )
    
    # `PasswordField` renders a text box that shows '*' as opposed to the actual characters
    password = PasswordField(
        'Password', 
        validators=[
            DataRequired(), 
            Length(8, 128)
        ]
    )
    
    # If we want to add a "Remember Me" checkbox manually, we can add it here 
    # Currently, we will remember users by defualt 
    # remember = BooleanField('Stay signed in')


class UpdateCredentials(ModelForm):
    
    current_password = PasswordField(
        'Current password',
        validators=[
            DataRequired(), 
            Length(8, 128), 
            ensure_existing_password_matches    # Makes sure password matches 
        ]
    )

    email = EmailField(
        'Email',
        validators=[
            Email(),
            Unique(User.email, get_session=lambda: db.session)    # Email must be unique 
        ]
    )
    
    password = PasswordField(
        'Password', 
        validators=[
            Optional(),       # Password is optional, since users may only want to update their email 
            Length(8, 128)
        ]
    )


class BeginPasswordResetForm(Form):
    
    identity = StringField(
        'Username or email',
        validators=[
            DataRequired(), 
            Length(5, 255), 
            ensure_identity_exists    # Make sure account can be found 
        ]
    )


class PasswordResetForm(Form):
    
    # Used to make sure serialized token matches
    reset_token = HiddenField()
    
    password = PasswordField(
        'Password', 
        validators=[
            DataRequired(), 
            Length(8, 128)
        ]
    )


class UpdateLocaleForm(Form):
    
    locale = SelectField(
        'Language preference', 
        validators=[DataRequired()],
        choices=choices_from_dict(LANGUAGES, prepend_blank=False)    # Allow selection from language settings 
    )
