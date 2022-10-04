from collections import OrderedDict

from flask_wtf import Form
import wtforms.ext
from wtforms import SelectField, StringField, BooleanField, HiddenField, IntegerField, FloatField, DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.validators import DataRequired, Length, Optional, Regexp, NumberRange
from wtforms_components import Unique

from libs.util_sqlalchemy import get_all_tournaments, get_all_countries, get_all_teams
from libs.util_wtforms import ModelForm, choices_from_dict
from badmintontv.blueprints.user.models import db, User


class SearchForm(Form):
    
    # Optional string field 
    # Note: `q` matches the variable in the search form macro 
    q = StringField(
        'Search terms', 
        validators=[
            Optional(), 
            Length(1, 255)
        ]
    )


class BulkDeleteForm(Form):
    
    # Query used in "All search results"
    q = HiddenField(
        'Search term',
        validators=[
            Optional(),
            Length(1, 10)
        ]
    )
    
    # Mapping lowercase strings to human-readable text
    SCOPE = OrderedDict([
        ('all_selected_items', 'All selected items'),
        ('all_search_results', 'All search results')
    ])

    scope = SelectField(
        'Privileges', 
        validators=[DataRequired()],
        choices=choices_from_dict(SCOPE, prepend_blank=False)   # Converts scope to select box in form 
    )


class UserForm(ModelForm):

    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Unique(
                User.username,
                get_session=lambda: db.session
            ),
            Optional(),
            Length(1, 30),
            # Part of the Python 3.7.x update included updating flake8 which means
            # we need to explicitly define our regex pattern with r'xxx'.
            Regexp(r'^\w+$', message='Letters, numbers and underscores only please.')
        ]
    )

    role = SelectField(
        'Privileges', 
        validators=[DataRequired()],
        choices=choices_from_dict(User.ROLE, prepend_blank=False)   # Converts dict role (from user model) to select box in form 
    )  
    
    # Label for checkbox field
    active = BooleanField('Yes, allow this user to sign in')


class UserCancelSubscriptionForm(Form):
    pass


class AddVideosForm(Form):
    pass

    
class VideoForm(Form):

    tournament = QuerySelectField(
        'Tournament',
        get_label='name',
        query_factory=get_all_tournaments
    )
    
    teams = QuerySelectMultipleField(
        'Teams',
        get_label='name',
        query_factory=get_all_teams
    )
    
    countries = QuerySelectMultipleField(
        'Counties',
        get_label='name',
        query_factory=get_all_countries
    )
        
    quality = StringField()
    
    date = DateField()
    round = StringField()
    discipline = StringField()


class TournamentForm(Form):
    
    name = StringField()
    
    
class TeamForm(Form):
    
    country = QuerySelectField(
        'Countries',
        get_label='name',
        query_factory=get_all_countries
    )
    
    name = StringField()
    
    
class CountryForm(Form):
    
    teams = QuerySelectMultipleField(
        'Teams',
        get_label='name',
        query_factory=get_all_teams
    )
    
    name = StringField()
