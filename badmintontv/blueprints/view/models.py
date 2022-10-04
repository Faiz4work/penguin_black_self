from sqlalchemy import or_

from libs.util_sqlalchemy import ResourceMixin, AwareDateTime
from badmintontv.extensions import db


class View(ResourceMixin, db.Model):
    
    __tablename__ = 'views'

    id = db.Column(db.Integer, primary_key=True)
    
    ip = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50))
    duration = db.Column(db.Time, nullable=False)
    
    # [View] One (View) to One (User)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'users.id',
            onupdate='CASCADE',
            ondelete='CASCADE'
        ),
        index=True,
        nullable=False
    )
    user = db.relationship('User')  # Bi-directional

    # [View] One (View) has One (Video)
    video_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'videos.id',
            onupdate='CASCADE',
            ondelete='CASCADE'
        ),
        index=True,
        nullable=False
    )
    video = db.relationship('Video')  # Bi-directional

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through: `username`, video `name`, view `country`

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        if query == '':
            return ''

        search_query = '%{}%'.format(query)
        
        from badmintontv.blueprints.user.models import User
        from badmintontv.blueprints.video.models import Video
        
        search_chain = (
            User.username.ilike(search_query),
            Video.name.ilike(search_query),
            View.country.ilike(search_query)
        )

        return or_(*search_chain)
