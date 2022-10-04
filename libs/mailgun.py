import os
from requests import post

from flask import render_template
import config.settings as config_settings
import instance.settings as instance_settings


class MailGunException(Exception):
    '''Custom MailGun exception'''
    def __init__(self, message: str):
        super().__init__(message)


class Mailgun:

    # Set Mailgun API key 
    try:
        MAILGUN_API_KEY = instance_settings.MAILGUN_API_KEY
    except:
        MAILGUN_API_KEY = config_settings.MAILGUN_API_KEY
    
    # Set Mailgun Domain name 
    try:
        MAILGUN_DOMAIN = instance_settings.MAILGUN_DOMAIN
    except:
        MAILGUN_DOMAIN = config_settings.MAILGUN_DOMAIN

    @classmethod
    def send_email(cls, FROM_title, FROM_email, email, subject, template_path, ctx, text=''):
        '''
        Sends an email from MailGun
        
        This function supports template rendering 
        
        Params:
            FROM_title (str):      Sent from title 
            FROM_email (str):      Send from email 
            email (str):           Emails to send to 
            subject (str):         Email subject 
            template_path (str):   Path to template to render in email
            ctx (dict):            Context variables we want the template to beable to access
            text (str):            Text in email 
                        
        Returns: Reponse
        '''

        if cls.MAILGUN_API_KEY is None:
            raise MailGunException('Failed to load API key')

        if cls.MAILGUN_DOMAIN is None:
            raise MailGunException('Failed to load domain')

        response = post(
            "https://api.mailgun.net/v3/{}/messages".format(cls.MAILGUN_DOMAIN),
            auth=("api", cls.MAILGUN_API_KEY),
            data={
                "from": "{} <{}>".format(FROM_title, FROM_email),
                "to": email,
                "subject": subject,
                "text": text,
                'html': cls.try_render_template(template_path, **ctx),
            },
        )

        if response.status_code != 200:
            raise MailGunException('Failed to send email')

        return response
    
    def try_render_template(template_path, **kwargs):
        '''
        Attempt to render a template
        
        We use a try/catch here to avoid having to do a path exists based on a 
        relative path to the template

        Params:
            template_path (str):   Template path
            kwargs (dict):         Variables that the template will have access to 
        
        Returns: Template 
        '''
        try:
            return render_template(template_path, **kwargs)
        except IOError:
            pass
