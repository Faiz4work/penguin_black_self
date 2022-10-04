from badmintontv.app import create_celery_app
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.billing.models.card import Card

celery = create_celery_app()


@celery.task()
def mark_old_credit_cards():
    '''
    Mark credit cards that:
    - Are going to expire soon, or 
    - Have expired

    Returns: Result of updating the records
    '''
    return Card.mark_old_credit_cards()

@celery.task()
def delete_users(ids):
    '''
    Delete users and potentially cancel their subscription

    Params:
        ids (list): List of ids to be deleted
    
    Returns: Number of users deleted
    '''
    return User.bulk_delete(ids)
