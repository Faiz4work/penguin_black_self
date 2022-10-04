from libs.mailgun import Mailgun
from badmintontv.app import create_celery_app

celery = create_celery_app()


@celery.task()
def deliver_contact_email(email, subject, text):
    '''
    Sends a contact e-mail

    Params:
        email (str):     E-mail address of the visitor
        subject (str):   E-mail subject
        text (str):      E-mail message
    '''
    
    ctx = {
        'email': email, 
        'subject': subject,
        'text': text
    }

    Mailgun.send_email(
        FROM_title='badmintontv.ai',
        FROM_email='wilson@wcai.dev',
        email=email,
        subject=subject,
        template_path='mail/index.html',
        ctx=ctx
    )
