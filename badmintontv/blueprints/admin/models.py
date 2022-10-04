from sqlalchemy import func

from badmintontv.blueprints.user.models import db, User
from badmintontv.blueprints.billing.models.subscription import Subscription


class Dashboard(object):
    
    @classmethod
    def group_and_count(cls, model, field):
        '''
        Perform a group by/count on a DB table/model on a given column 
        
        Params:
            model (SQLAlchemy model):   Model to count on 
            field (SQLAlchemy field):   Column to count 

        Returns: Dictionary of counts per group
        '''
        return Dashboard._group_and_count(model, field)

    @classmethod
    def _group_and_count(cls, model, field):
        '''
        Group results for a specific model and field.

        Params:
            model (SQLAlchemy model):    Name of the model
            field (SQLAlchemy field):    Name of the field to group on
        
        Returns: Dictionary of counts per group
        '''
        
        # Count query 
        count = func.count(field)
        
        # Looks through all users and gives us the number of users for each role, ordered from most-to-least counts
        query = db.session.query(count, field).group_by(field).order_by(count.desc()).all()

        results = {
            'query': query,
            'total': model.query.count()   # Total number of entries
        }
        return results
