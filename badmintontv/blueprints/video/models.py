import datetime
import math 

from sqlalchemy import or_
from sqlalchemy.sql.expression import extract

from libs.util_sqlalchemy import ResourceMixin, AwareDateTime
from badmintontv.extensions import db
from badmintontv.blueprints.view.models import View

# Association table for many-to-many relationship of Video/Team
videos_teams = db.Table(
    "videos_teams",
    db.Column(
        "video_id", 
        db.ForeignKey(
            "videos.id",
            onupdate='CASCADE',
            ondelete='SET NULL'
        )
    ),
    db.Column(
        "team_id", 
        db.ForeignKey(
            "teams.id",
            onupdate='CASCADE',
            ondelete='SET NULL'
        )
    ),
)


class Tournament(ResourceMixin, db.Model):
    
    __tablename__ = 'tournaments'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # [Tournament] One (Tournament) has Many (Videos)
    videos = db.relationship(
        'Video',
        backref='tournaments',
        passive_deletes=True
    )

    def __init__(self, name, start_date, end_date):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
    
    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter(
            cls.name == name
        ).first()
    
    @classmethod
    def find_by_year(cls, year):
        return cls.query.filter(
            extract('year', cls.start_date) == year
        ).order_by(cls.start_date.desc())
    
    @classmethod
    def find_latest(cls, today=datetime.datetime.today().date()):
        '''Get latest tournament'''
        
        # Find the closest events which are greater/less than the timestamp
        gt_event = cls.query.filter(
                cls.start_date > today
            ).order_by(
                cls.start_date.asc()
            ).first()
        
        lt_event = cls.query.filter(
                cls.start_date < today
            ).order_by(
                cls.start_date.desc()
            ).first()

        # Find diff between events and the timestamp 
        # Note: If no event found, default to infintiy
        gt_diff = (gt_event.start_date - today).total_seconds() if gt_event else math.inf
        lt_diff = (today - lt_event.start_date).total_seconds() if lt_event else math.inf

        # Return the newest event, if it's closer to the timestampe, else older event
        # Note: If an event is None, its diff will always be greater (since we set it to infinity)
        return gt_event if gt_diff < lt_diff else lt_event
    
    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through: `name`

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        if query == '':
            return ''

        search_query = '%{}%'.format(query)
        
        search_chain = (
            Tournament.name.ilike(search_query),
        )

        return or_(*search_chain)


class Team(ResourceMixin, db.Model):
    
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False)

    # [Team] One (Team) has Many (Videos)
    videos = db.relationship(
        'Video', 
        secondary='videos_teams', 
        back_populates='teams'
    )
    
    # [Team] One (Team) to One (Country)
    country_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'countries.id',
            onupdate='CASCADE',
            ondelete='SET NULL'  # If a Country is deleted, we DO NOT delete its Teams
        ),
        index=True, 
        nullable=True
    )
    country = db.relationship('Country')


    def __init__(self, name, country):
        self.name = name
        self.country = country
    
    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter(
            cls.name == name
        ).first()
    
    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through: `name`

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        if query == '':
            return ''

        search_query = '%{}%'.format(query)
        
        search_chain = (
            Team.name.ilike(search_query),
        )

        return or_(*search_chain)


class Country(ResourceMixin, db.Model):
    
    __tablename__ = 'countries'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False)
    
    # [Country] One (Country) has Many (Teams)
    teams = db.relationship(
        'Team',
        backref='countries',
        passive_deletes=True
    )
    
    def __init__(self, name):
        self.name = name
    
    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter(
            cls.name == name
        ).first()
    
    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through: `name`

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        if query == '':
            return ''

        search_query = '%{}%'.format(query)
        
        search_chain = (
            Country.name.ilike(search_query),
        )

        return or_(*search_chain)


class Video(ResourceMixin, db.Model):

    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)


    # ---------------------------------------------
    # --------------- Details ---------------
    # ---------------------------------------------

    folder = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String(120), nullable=False)

    highlights_datetime = db.Column(AwareDateTime(), nullable=False)
    highlights_type = db.Column(db.String(30), nullable=False)
    highlights_filename = db.Column(db.String(150), nullable=False)
    highlights_duration = db.Column(db.Time, nullable=False)

    date = db.Column(db.Date, nullable=False)
    round = db.Column(db.String(25), nullable=False)
    discipline = db.Column(db.String(15), nullable=False)
    
    model_name = db.Column(db.String(150), nullable=False)


    # ---------------------------------------------
    # --------------- Relationships ---------------
    # ---------------------------------------------

    # [Video] One (Video) to One (Tournament)
    tournament_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'tournaments.id',
            onupdate='CASCADE',
            ondelete='SET NULL'  # If a Tournament is deleted, we DO NOT delete its Videos
        ),
        index=True, 
        nullable=True
    )
    tournament = db.relationship('Tournament')
    
    # [Video] One (Video) has Many (Team)
    teams = db.relationship(
        'Team', 
        secondary='videos_teams',
        back_populates='videos',
        passive_deletes=True
    )

    # [Video] One (Video) has Many (Views)
    views = db.relationship(
        View,
        backref='videos',
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        super(Video, self).__init__(**kwargs)

    @classmethod
    def find_by_folder_name_highlights_type(cls, folder, name, highlights_type):        
        return cls.query.filter_by(
            folder=folder,
            name=name,
            highlights_type=highlights_type
        ).first()
        
    @classmethod
    def find_by_id_highlights_type(cls, id, highlights_type):
        return cls.query.filter_by(
            id=id,
            highlights_type=highlights_type
        ).first()

    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through:
            - folder
            - name
            - highlights_type
            - round
            - discipline

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        # Return empty string if there's no search query
        if query == '':
            return ''

        # This tells SQLAlchemy that we want to search for partial-words 
        search_query = '%{}%'.format(query)
        
        # Search fields
        search_chain = (
            Video.folder.ilike(search_query),
            Video.name.ilike(search_query),
            Video.highlights_type.ilike(search_query),
            Video.round.ilike(search_query),
            Video.discipline.ilike(search_query),
        )

        # Allow matching to work on email, username, OR both  
        # Note: Alternatively, `and_` returns results on email AND username 
        return or_(*search_chain)
    
