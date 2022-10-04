import datetime

from flask import request
from sqlalchemy import DateTime, text
from sqlalchemy.types import TypeDecorator

from libs.util_datetime import tzware_datetime
from badmintontv.extensions import db


def get_all_tournaments():
    
    from badmintontv.blueprints.video.models import Tournament
    
    return db.session.query(Tournament).all()
    

def get_all_teams():
    
    from badmintontv.blueprints.video.models import Team
    
    return db.session.query(Team).all()


def get_all_countries():
    
    from badmintontv.blueprints.video.models import Country
    
    return db.session.query(Country).all()
    

def sort_order(model, sort_default='created_on', direction_default='desc', prepend=''):
    '''
    Gets sort order for SQLAlchemy model filtering 
    
    eg.
        order_values='views.created_on desc'
    
    Params:
        model (SQLAlchemy Model)
        sort_default (str):       Default field to sort on, if `sort` isn't supplied
        direction_default (str):  Default direction to sort on if `direction` isn't supplied
        prepend (str):            Add this to the beginning of the query (used in conjuction with JOIN)
    '''
    
    # Get values  
    sort = request.args.get('sort', sort_default)
    direction = request.args.get('direction', direction_default)
    
    # Assign
    sort_by = model.sort_by(sort, direction)
    
    # Order for SQLAlchemy
    order_values = '{}{} {}'.format(prepend, sort_by[0], sort_by[1])
    
    return order_values


def simple_paginate(model, order_values, page, default_q='', num_items=50):
    '''
    Paginate a queried model and count its filtered rows
    
    Params:
        model (SQLAlchemy Model)
        order_values (str):       Sort field and direction, given by `sort_order`
        page (int):               Page number 
        default_q (str):          Default query if `q` isn't supplied 
        num_items (int):          Number of items per page 
    
    Returns:
        model_paginated (...):   Paginated model 
        count (int):             Number of rows in filtered model 
    '''
    
    # Query model 
    model_queried = model.query.filter(
            model.search(query=text(request.args.get('q', default_q))) \
        )
    
    # Count number of rows 
    model_count = model_queried.count()
    
    # Paginate
    model_paginated = model_queried.order_by(
            # Text-based sorting 
            text(order_values)
        # `True`: Will throw an error if the page doesn't exist 
        ).paginate(page, num_items, True)
    
    return model_paginated, model_count


def paginate(model, on_top, order_values, page, default_q='', num_items=50):
    '''
    Similar to `simple_paginate`, but field `on_top` (SQLAlchemy Field) 
    takes priority in ordering
    '''
    
    model_queried = model.query.filter(
            model.search(query=text(request.args.get('q', default_q))) \
        )
        
    model_count = model_queried.count()
    
    model_paginated = model_queried.order_by(
            # Keep these rows on top
            on_top,
            text(order_values)
        ).paginate(page, num_items, True)
    
    return model_paginated, model_count 
        

def paginate_join(model, model_join_on, order_values, page, default_q='', num_items=50):
    '''
    Similar to `simple_paginate`, but we join on `model_join_on` (SQLAlchemy model)
    before filtering 
    
    This makes it so that we can access `model_join_on`'s fields in `model.search`
    during filtering 
    '''
    
    model_queried = model.query.join(
            # This allows us to access `model_join_on`'s fields 
            model_join_on
        ).filter(
            model.search(query=text(request.args.get('q', default_q))) \
        )
    
    model_count = model_queried.count()
    
    model_paginated = model_queried.order_by(            
            text(order_values)
        ).paginate(page, num_items, True)
    
    return model_paginated, model_count


def paginate_joins(model, models_join_on, order_values, page, default_q='', num_items=50):
    '''
    Same as `paginate_join` except `models_join_on` (list of 2 SQLAlchemy models)
    is supplied 2 models 
    '''
    
    model_queried = model.query.join(
            models_join_on[0]
        ).join(
            models_join_on[1]
        ).filter(
            model.search(query=text(request.args.get('q', default_q))) \
        )
    
    model_count = model_queried.count()
    
    model_paginated = model_queried.order_by(            
            text(order_values)
        ).paginate(page, num_items, True)
    
    return model_paginated, model_count


class AwareDateTime(TypeDecorator):
    '''
    A custom DateTime type which can only store `tz-aware` DateTimes

    Source: https://gist.github.com/inklesspen/90b554c864b99340747e
    '''
    
    impl = DateTime(timezone=True)

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            raise ValueError('{!r} must be TZ-aware'.format(value))
        return value

    def __repr__(self):
        return 'AwareDateTime()'


class ResourceMixin(object):
    '''Adds common functionality to any SQLAlchemy-driven model'''
    
    # Keeps track when record was created
    created_on = db.Column(
        AwareDateTime(),
        default=tzware_datetime
    )
    
    # Keeps track when a record was updated
    updated_on = db.Column(
        AwareDateTime(),
        default=tzware_datetime,
        onupdate=tzware_datetime
    )
    
    @classmethod
    def sort_by(cls, field, direction):
        '''
        Validate the sort field and direction

        Params:
            field (str):       Field name
            direction (str):   Direction
        
        Returns: `(field, direction)` tuple
        '''
        
        # Default `field` to `created_on` if the field doesn't exist
        # This is a safety check incase a user changes the URL manually
        if field not in cls.__table__.columns:
            field = 'created_on'
        
        # Make sure `direction` is either ascending or descending 
        if direction not in ('asc', 'desc'):
            direction = 'asc'

        return field, direction

    @classmethod
    def get_bulk_action_ids(cls, scope, ids, omit_ids=[], query=''):
        '''
        Determine which IDs are to be modified

        Params:
            scope (str):      Affect all or only a subset of items; Either:
                              - 'all_selected_items', or 
                              - 'all_search_results'
                              
            ids (list):       List of ids to be modified
            omit_ids (list):  Remove 1 or more IDs from the list
            query (str):     Search query (if applicable)
        
        Returns: List of IDs to modify
        '''
        
        # Make sure all IDs are strings 
        omit_ids = [str(id) for id in omit_ids]   # Also works: `list(map(str, omit_ids))``

        
        # If there's a search term, and we selected 'All search results'
        # Note: If there's no search term (`query is None`), 
        #       we'll treat it as if "All selected items" are checked
        #       This is because '' shouldn't be treated as a search result that matches everything 
        if query and scope == 'all_search_results':
            
            # Change the scope to go from selected ids to all search results
            ids = cls.query.with_entities(cls.id).filter(cls.search(query))

            # SQLAlchemy returns back a list of tuples, we want a list of strings
            ids = [str(item[0]) for item in ids]

        # Remove 1 or more items from the list
        # This is useful when you want to protect the current user from deleting 
        # themself when bulk deleting user accounts
        if omit_ids:
            ids = [id for id in ids if id not in omit_ids]

        return ids

    @classmethod
    def bulk_delete(cls, ids):
        '''
        Delete 1 or more model instances

        Params:
            ids (list): List of ids to be deleted
        
        Returns: 
            delete_count (int): Number of deleted instances
        '''
        
        delete_count = cls.query.filter(cls.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        
        return delete_count
    
    def save(self):
        '''
        Save a model instance

        Returns: Model instance
        '''
        db.session.add(self)
        db.session.commit()

        return self

    def delete(self):
        '''
        Delete a model instance

        Returns: `db.session.commit()`'s result
        '''
        db.session.delete(self)
        return db.session.commit()

    def __str__(self):
        '''Return a human readable version of a class instance'''
        
        obj_id = hex(id(self))
        columns = self.__table__.c.keys()

        values = ', '.join("%s=%r" % (n, getattr(self, n)) for n in columns)
        return '<%s %s(%s)>' % (obj_id, self.__class__.__name__, values)
