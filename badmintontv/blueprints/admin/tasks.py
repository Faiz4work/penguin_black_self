from badmintontv.app import create_celery_app

celery = create_celery_app()


@celery.task()
def delete_rows(model, ids):
    '''
    Delete rows from a model

    Params:
        ids (list): List of ids to be deleted
    
    Returns: Number of rows deleted
    '''
    return model.bulk_delete(ids)
