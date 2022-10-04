import os 
import json
import datetime 
from flask import Blueprint, render_template, current_app, flash
from flask_login import login_required

from config import settings
from libs.util_datetime import localize_datetime
from badmintontv.blueprints.admin.models import Dashboard
from badmintontv.blueprints.admin.forms import AddVideosForm
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.user.decorators import role_required
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.video.models import Video, Tournament, Team, Country, videos_teams
from badmintontv.blueprints.view.models import View

admin = Blueprint(
    'admin', 
    __name__, 
    template_folder='../templates', 
    url_prefix='/admin'
)


@admin.before_request     # This is called before all other functions
@login_required
@role_required('admin')     # Make sure user is an admin 
def before_request():
    '''Protect all of the admin endpoints by making sure user is logged in and is an admin'''
    pass


@admin.route('', methods=['GET', 'POST'])   # `/admin`, due to `url_prefix` in blueprint
def dashboard():
    '''Renders a template with count information for groups in DB'''
    
    # Set-up empty form 
    form = AddVideosForm()
    
    add = False
    new_videos_metadata, num_new_videos = _new_videos(add=add)

    # POST request to add new videos 
    if form.validate_on_submit():
        
        add = True
        new_videos_metadata, num_new_videos = _new_videos(add=add)
        
        # If there were videos added, flash success message
        if num_new_videos > 0:
            flash('{} videos added'.format(num_new_videos), 'success')
            
        # Flash error message
        else:
            flash('No videos to add', 'error')
    
    group_and_count_users = Dashboard.group_and_count(
        model=User,
        field=User.role
    )
    
    group_and_count_plans = Dashboard.group_and_count(
        model=Subscription,
        field=Subscription.plan_id
    )
    
    group_and_count_region = Dashboard.group_and_count(
        model=User,
        field=User.current_sign_in_region
    )
    
    group_and_count_locale = Dashboard.group_and_count(
        model=User,
        field=User.locale
    )
    
    group_and_count_view = Dashboard.group_and_count(
        model=View,
        field=View.country
    )

    return render_template(
        'admin/page/dashboard.html', 
        form=form,
        add=add,
        new_videos_metadata=new_videos_metadata,
        num_new_videos=num_new_videos,
        group_and_count_users=group_and_count_users,
        group_and_count_plans=group_and_count_plans,
        group_and_count_region=group_and_count_region,
        group_and_count_locale=group_and_count_locale,
        group_and_count_view=group_and_count_view,
        prices=settings.STRIPE_PRICES,
        LANGUAGES=settings.LANGUAGES
    )


def _new_videos(add=False):
    '''
    Creates all tournaments & matches in the `config.VID_DIR` folder
    
    Metadata is added using the following files for each match:
    - `metadata_run.json` 
    - `metadata_match.json`
    
    Note: `tournament_folder`, `match_folder` and `highlights_type` can never be 
    updated since we use them to search for the corresponding video
    
    Params:
        add (bool): If True, add new videos; False to just return their metadata
    
    Returns:
        new_videos_metadata (dict):   ...
        num_new_videos (int):       ...
    '''
        
    # Used to save changes
    new_videos_metadata = {}
    num_new_videos = 0

    # Loop over tournaments listed 
    tournaments = os.listdir(current_app.config['VID_DIR'])
    for tournament in tournaments:
        
        tournament_dir = os.path.join(
            current_app.config['VID_DIR'], 
            tournament
        )
        
        # Skip system-generated folders 
        if tournament.startswith('.') or tournament.startswith('@'):
            continue

        # Check all matches in tournament 
        for match in os.listdir(tournament_dir):
            
            match_dir = os.path.join(tournament_dir, match)
            
            # Skip system-generated folders 
            if match.startswith('.') or match.startswith('@'):
                continue
            
            # Metadata paths 
            metadata_run_path = os.path.join(
                match_dir, 
                current_app.config['METADATA_RUN_FILENAME']
            )
            
            metadata_match_path = os.path.join(
                match_dir, 
                current_app.config['METADATA_MATCH_FILENAME']
            )
            
            # If both metadata files exists, update DB 
            if os.path.exists(metadata_run_path) and os.path.exists(metadata_match_path):
                
                # Load metadata
                metadata_run = json.load(open(metadata_run_path))
                metadata_match = json.load(open(metadata_match_path))
                
                # Add video entries for each of the video types
                for highlights_type in ['Highlights', 'Extended Highlights']:
                
                    highlights_filename = '[{}] {}'.format(highlights_type, metadata_run['match_filename'])
                    
                    highlights_duration = metadata_run['version_to_metadata']['3']['duration_highlights'] \
                        if highlights_type == 'Extended Highlights' \
                        else metadata_run['version_to_metadata']['3']['duration_filtered_highlights']
                    
                    # Search for video in DB
                    video = Video.find_by_folder_name_highlights_type(
                        folder=tournament, 
                        name=match,
                        highlights_type=highlights_type
                    )
                        
                    # If video doesn't exist, create it  
                    if not video:
                        
                        # ----------------------------------------------
                        # ---------------- Prepare data ----------------
                        # ----------------------------------------------
                        
                        # `str` --> `datetime.date`
                        year, month, day = metadata_match['date'].split('-')
                        date = datetime.date(
                            int(year), int(month), int(day)
                        )
                        
                        # Make sure `datetime` is aware
                        try:
                            highlights_datetime = localize_datetime(
                                datetime.datetime.strptime(
                                    metadata_run['datetime'], 
                                    '%Y-%m-%d %H:%M:%S'
                                )
                            )
                        except:
                            highlights_datetime = datetime.datetime.strptime(
                                metadata_run['datetime'], 
                                '%Y-%m-%d %H:%M:%S'
                            )
                        
                        # ----------------------------------------------
                        # --------------- Create entries ---------------
                        # ----------------------------------------------
                        
                        # Tournament 
                        name = metadata_match['tournament']
                        tournament_obj = create_tournament(name, date)
                        
                        # Countries 
                        country1 = metadata_match['country1']
                        country2 = metadata_match['country2']
                        countries = create_countries(country1, country2)
                        
                        # Teams
                        team1 = metadata_match['team1']
                        team2 = metadata_match['team2']
                        teams = create_teams(team1, team2, country1, country2)
                        
                        # Video                         
                        metadata = {
                            'folder': metadata_run['tournament_folder'],
                            'name': metadata_run['match_folder'],
                            'filename': metadata_run['match_filename'],
                            
                            'highlights_datetime': highlights_datetime,
                            'highlights_type': highlights_type,
                            'highlights_filename': highlights_filename,
                            'highlights_duration': highlights_duration,
                            
                            'date': date,
                            'round': metadata_match['round'] if metadata_match['round'] is not None else 'Not Recognized',
                            'discipline': metadata_match['discipline'] if metadata_match['discipline'] is not None else 'Not Recognized',
                            
                            # Relationships 
                            'tournament_id': tournament_obj.id,
                            'teams': teams,
                            
                            # AI metadata
                            'model_name': metadata_run['tasks']['Action Spotting']['model_name']
                        }
                        
                        # Add new video to DB 
                        if add:
                            video = Video(**metadata)
                            video.save()
                        
                        # Make sure key exists 
                        folder = metadata['folder']
                        if folder not in new_videos_metadata:
                            new_videos_metadata[folder] = []
                        
                        # Note this tournament-match-highlights combo
                        new_videos_metadata[folder].append({
                            'name': metadata['name'],                                
                            'highlights_type': metadata['highlights_type'],
                        })
                        
                        num_new_videos += 1

    return new_videos_metadata, num_new_videos


def create_tournament(name, date):
    '''
    Ensures tournament with `name` is in DB, and its start-end dates are updated
    
    Returns:
        tournament (Tournament)
    '''

    # Dummy name 
    if name is None:
        name = 'Not Recognized'
    
    tournament = Tournament.find_by_name(name)

    if not tournament:
        tournament = Tournament(
            name=name,
            start_date=date,
            end_date=date
        )
        tournament.save()
    
    # Edit start-end dates
    else:
        
        # Start date 
        if date < tournament.start_date:
            tournament.start_date = date
        
        # End date 
        if date > tournament.end_date:
            tournament.end_date = date
        
        tournament.save()
    
    return tournament


def create_countries(country1, country2):
    '''
    Ensures countries `country1` and `country2` are in DB
    
    Returns:
        countries (list): List of `Country` entities 
    '''

    countries = []
    for name in [country1, country2]:
        
        # Dummy name 
        if name is None:
            name = 'Not Recognized'
        
        country = Country.find_by_name(name)
        if not country:
            country = Country(name)
            country.save()
        
        countries.append(country)
    
    return countries


def create_teams(team1, team2, country1, country2):
    '''
    Ensures teams `team1` and `team2` are in DB
    
    Returns:
        teams (list): List of `Team` entities 
    '''
    
    # Get countries 
    country1 = Country.find_by_name(country1)
    country2 = Country.find_by_name(country2)

    teams = []
    for name, country in [(team1, country1), (team2, country2)]:
        
        # Dummy name 
        if name is None:
            name = 'Not Recognized'
        
        team = Team.find_by_name(name)
        if not team:
            team = Team(name, country)
            team.save()
        
        teams.append(team)
    
    return teams
