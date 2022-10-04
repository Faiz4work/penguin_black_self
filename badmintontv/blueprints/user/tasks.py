from libs.mailgun import Mailgun 
from badmintontv.app import create_celery_app
from badmintontv.blueprints.user.models import User

celery = create_celery_app()


@celery.task()
def deliver_signup_email(user_id, signup_token):
    '''
    Sends a confirmation email to a user 
    
    Params:
        user_id (int):       User ID 
        signup_token (str):  Serialized token
    '''
    
    user = User.query.get(user_id)
    
    ctx = {
        'user': user, 
        'signup_token': signup_token
    }

    Mailgun.send_email(
        FROM_title='badmintontv.ai',
        FROM_email='wilson@wcai.dev',
        email=user.email,
        subject='[badmintontv.ai] Signup Confirmation',
        template_path='mail/signup_confirmation.html',
        ctx=ctx
    )


@celery.task()
def deliver_password_reset_email(user_id, reset_token):
    '''
    Send a reset password e-mail to a user

    Params:
        user_id (int):       User ID 
        reset_token (str):   Serialized token
    '''
    
    # Get user by ID (instead of passing in user object) 
    # This covers an edge case, where a user changes their email before this task is finished executing
    # In this case, the email would be sent to an email not linked to an account 
    user = User.query.get(user_id)
    
    # Make sure user exists 
    if user is None:
        return

    ctx = {
        'user': user, 
        'reset_token': reset_token
    }

    Mailgun.send_email(
        FROM_title='badmintontv.ai',
        FROM_email='wilson@wcai.dev',
        email=user.email,
        subject='[badmintontv.ai] Password reset',
        template_path='mail/password_reset.html',
        ctx=ctx
    )
