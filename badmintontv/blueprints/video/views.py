import os
import json
import datetime

from flask import Blueprint, request, current_app, render_template
from flask_login import login_required

from badmintontv.blueprints.billing.decorators import video_lock
from badmintontv.blueprints.user.decorators import anonymous_required, role_required
from badmintontv.blueprints.video.models import Video, Tournament, Team, Country, videos_teams
from badmintontv.blueprints.video.template_processors import format_country

video = Blueprint(
    'video', 
    __name__, 
    template_folder='templates',
    # url_prefix='/video'
)


# -------------------------------------------
# ----------------- Level 1 -----------------
# -------------------------------------------

# [Matches] Latest tournament 
@video.route('/latest_tournament', methods=['GET'])
def latest_tournament():
    '''
    Retrieves all matches from the latest tournament
    
    Order: Newest-to-Oldest
    '''

    tournament = Tournament.find_latest()
    
    # Safety check 
    if tournament:
    
        # Get all videos that include this team 
        videos_queried = Video.query.join(Tournament).filter(
            Tournament.name == tournament.name
        )
        
        tournaments_to_videos = _sort_videos_by_tournament(videos_queried)
    
    else:
        tournaments_to_videos = []
        
    return render_template(
        'matches.html',
        title='Latest Tournament',
        query='_',
        tournaments_to_videos=tournaments_to_videos,
        back_route='_',
        from_route='video.latest_tournament'
    )


# [Tournaments] All tournaments 
@video.route('/tournaments', methods=['GET'])
def tournaments():
    '''
    Retrieves all tournament years
    
    Order: Newest-to-Oldest
    '''
    
    query = Tournament.query.with_entities(Tournament.start_date).distinct()
    start_dates = [row.start_date for row in query.all()]
    years = sorted(list(set([start_date.year for start_date in start_dates])), reverse=True)
    
    return render_template(
        'tournaments.html',
        years=years
    )    
    

# [Teams] All teams
@video.route('/teams', methods=['GET'])
def teams():
    '''
    Retrieves all teams
    
    Order: Alphabetical
    '''

    teams = Team.query.order_by(Team.name.asc())
    
    return render_template(
        'teams.html',
        teams=teams,
    )
    



# [Country] All countries
@video.route('/countries', methods=['GET'])
def countries():
    '''
    Retrieves all countries
    
    Order: Alphabetical
    '''
    
    countries = Country.query.order_by(Country.name.asc())
    # countries = ['home','india','pakistan']
    print(countries)
    return render_template(
        'countries.html',
        countries=countries,
    )


# -------------------------------------------
# ----------------- Level 2 -----------------
# -------------------------------------------

# [Matches] Any tournament 
@video.route('/tournament_to_matches', defaults={'query': '2022'})
@video.route('/tournament_to_matches/<string:query>', methods=['GET'])
def tournament_to_matches(query):
    '''
    Retrieves all matches from a tournament year, grouped by tournament
    
    Order: Newest-to-Oldest
    '''
    
    lower_bound = '{}-12-31'.format(int(query)-1)
    upper_bound = '{}-01-01'.format(int(query)+1)
    
    # Get all videos where the tournament is in year `query`
    videos_queried = Video.query.join(Tournament).filter(
        lower_bound <= Tournament.start_date
    ).filter(
        Tournament.start_date <= upper_bound
    )
    
    tournaments_to_videos = _sort_videos_by_tournament(videos_queried)
        
    return render_template(
        'matches.html',
        title=query,
        query=query,
        tournaments_to_videos=tournaments_to_videos,
        back_route='video.tournaments',
        from_route='video.tournament_to_matches'
    )
    

# [Matches] Any team 
@video.route('/team_to_matches', defaults={'query': 'Kento Momota'})
@video.route('/team_to_matches/<string:query>', methods=['GET'])
def team_to_matches(query):
    '''
    Retrieves all matches for a team, grouped by tournament
    
    Order: Newest-to-Oldest
    '''
    
    # Get all videos that include this team 
    videos_queried = Video.query.join(videos_teams).join(Team).filter(
        Team.name == query
    )
    
    tournaments_to_videos = _sort_videos_by_tournament(videos_queried)
    
    # Edit tile to include country 
    team = Team.find_by_name(query)
    title = '{} ({})'.format(query, team.country.name)
    
    return render_template(
        'matches.html',
        title=title,
        query=query,
        tournaments_to_videos=tournaments_to_videos,
        back_route='video.teams',
        from_route='video.team_to_matches'
    )
    

# [Matches] Any country 
@video.route('/country_to_matches', defaults={'query': 'JPN'})
@video.route('/country_to_matches/<string:query>', methods=['GET'])
def country_to_matches(query):
    '''
    Retrieves all matches for a country, grouped by tournament
    
    Order: Newest-to-Oldest
    '''
    
    # Get all videos that include this team 
    videos_queried = Video.query.join(videos_teams).join(Team).join(Country).filter(
        Country.name == query
    )
    
    tournaments_to_videos = _sort_videos_by_tournament(videos_queried)
    
    return render_template(
        'matches.html',
        title=format_country(query),
        query=query,
        tournaments_to_videos=tournaments_to_videos,
        back_route='video.countries',
        from_route='video.country_to_matches'
    )
    

def _sort_videos_by_tournament(videos_queried):
    '''
    Helper function to group videos (sorted by date from newest-to-oldest) by their corresponding tournament
    
    Params:
        videos_queried (...): Queried result from `Video` model
        
    Returns:
        tournaments_to_videos (dict): Mapping a `Tournament` to sorted lists of `Video`s, 
    '''
    
    # Unique list of all tournaments from `videos`, sorted from newest-to-oldest
    tournaments = [video.tournament for video in videos_queried]
    tournaments = sorted(list(set(tournaments)), key=lambda x: x.start_date, reverse=True)

    tournaments_to_videos = {}
    for tournament in tournaments:
        
        # Unique list of all videos from `videos`, if it belongs to this tournament, sorted from newest-to-oldest
        videos_filtered = [video for video in videos_queried if video.tournament.name == tournament.name]
        videos_sorted = sorted(videos_filtered, key=lambda x: x.date, reverse=True)
        
        # Save it 
        tournaments_to_videos[tournament] = videos_sorted
    
    return tournaments_to_videos


# -------------------------------------------
# ----------------- Level 3 -----------------
# -------------------------------------------

# Video player 
@video.route('/match', defaults={
    'id': 1,
    'highlights_type': 'Extended Highlights',
    'from_route': '_',
    'query': '_'
})
@video.route('/match/<int:id>/<string:highlights_type>/<string:from_route>/<string:query>', methods=['GET'])
@video_lock
def match(id, highlights_type, from_route, query):
    '''Retrieves a single match, given it's `id`, and `highlights_type`'''
    
    video = Video.find_by_id_highlights_type(id, highlights_type)
    
    video_path = os.path.join(
        current_app.config['VID_DIR'],
        video.folder,
        video.name,
        '[{}] {}'.format(video.highlights_type, video.filename)
    )
    
    return render_template(
        'match.html',
        video=video,
        video_path=video_path,
        back_route=from_route,
        query=query
    )
