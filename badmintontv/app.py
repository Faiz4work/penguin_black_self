import os 
import logging
import datetime 
import stripe 

from itsdangerous import URLSafeTimedSerializer
from flask import Flask, render_template, request, session
from flask_login import current_user
from celery import Celery
from logging.handlers import SMTPHandler
from werkzeug.middleware.proxy_fix import ProxyFix

from badmintontv.blueprints.admin.views.dashboard import admin
from badmintontv.blueprints.page.views import page
from badmintontv.blueprints.contact.views import contact
from badmintontv.blueprints.user.views import user
from badmintontv.blueprints.billing.views.billing import billing
from badmintontv.blueprints.billing.views.stripe_webhook import stripe_webhook
from badmintontv.blueprints.video.views import video
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.billing.template_processors import format_currency, current_year
from badmintontv.blueprints.admin.template_processors import hms_to_s
from badmintontv.blueprints.video.template_processors import format_country
from badmintontv.extensions import debug_toolbar, csrf, db, login_manager, babel

# List of Celery tasks 
CELERY_TASK_LIST = [
    'badmintontv.blueprints.contact.tasks',
    'badmintontv.blueprints.user.tasks',
    'badmintontv.blueprints.billing.tasks',
    'badmintontv.blueprints.admin.tasks',
]


def create_celery_app(app=None):
    '''
    Creates a new Celery object and ties together the Celery config to the app's config
    
    Wrap all tasks in the context of the application.

    Params:
        app: Flask app
        
    Returns: 
        celery: Celery app
    '''
    
    app = app or create_app()

    celery = Celery(
        app.import_name, 
        broker=app.config['CELERY_BROKER_URL'],
        include=CELERY_TASK_LIST
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        '''Sets-up a context for each task'''
        
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    
    return celery


def create_app(settings_override=None):
    '''
    Create Flask app using app factory pattern
    
    Params:
        settings_override (dict): ...
    '''
    
    # `instance_relative_config`: Look for instance module in the same directory as main nmodule
    app = Flask(__name__, instance_relative_config=True)

    
    # --------------------------------------------------
    # -------------------- Settings --------------------
    # --------------------------------------------------
    
    # Loook for `settings` module in `/config`
    app.config.from_object('config.settings')
    
    # Load `settings.py` from `/config`
    # `silent`: Don't crash Flask if file doesn't exist 
    app.config.from_pyfile('settings.py', silent=True)
    
    '''
    Note: If there's a `settings.py` file in `/instance`, 
    the settings there will override their `/config` counterparts
    
    This is typically used for production settings
    '''
    
    # Set log level 
    app.logger.setLevel(app.config['LOG_LEVEL'])
    
    # Set-up Stripe
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
    stripe.api_version = app.config.get('STRIPE_API_VERSION')
    
    # Optimize Jinja templates in browser
    app.jinja_env.lstrip_blocks = True  # Remove previous spacing on this line 
    app.jinja_env.trim_blocks = True  # Remove newlines 

    
    # --------------------------------------------------------
    # ------------------ Middleware, Errors ------------------
    # --------------------------------------------------------
    
    middleware(app)
    error_templates(app)
    exception_handler(app)
    
    
    # ----------------------------------------------------
    # -------------------- Blueprints --------------------
    # ----------------------------------------------------
    
    app.register_blueprint(admin)
    app.register_blueprint(page)
    app.register_blueprint(contact)
    app.register_blueprint(user)
    app.register_blueprint(billing)
    app.register_blueprint(stripe_webhook)
    app.register_blueprint(video)
    
    
    # -------------------------------------------------------
    # ------------------------ Tests ------------------------
    # -------------------------------------------------------
    
    if settings_override:
        app.config.update(settings_override)
    
    # ------------------------------------------------------
    # --------------------- Extensions ---------------------
    # ------------------------------------------------------
    
    # Add custom Jinja template processors 
    template_processors(app)
    
    # Add custom extensions 
    extensions(app)
    
    # Add authentication to User model
    authentication(app, User)
    
    # Localization
    locale(app)

    return app


def extensions(app):
    '''
    Register any number of extensions (mutates the app passed in)

    Params:
        app: Flask application instance
    '''

    # debug_toolbar.init_app(app)
    csrf.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app)


def template_processors(app):
    '''
    Register 0 or more custom (Jinja) template processors (mutates the app passed in)

    Params:
        app: Flask application instance

    Returns: App jinja environment
    '''
    
    # Allow these filters to be called from any template 
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['hms_to_s'] = hms_to_s
    app.jinja_env.filters['format_country'] = format_country
    
    # Allow this variable to be used in any template 
    app.jinja_env.globals.update(current_year=current_year)

    return app.jinja_env


def authentication(app, user_model):
    '''
    Initializes the Flask-Login extension (mutates the app passed in)

    Params:
        app:                             Flask application instance
        user_model (SQLAlchemy model):   Model that contains the authentication information
    '''
    
    # Tells Flask-Login that our login logic is in the view `user.login`
    login_manager.login_view = 'user.login'

    @login_manager.user_loader
    def load_user(uid):
        '''
        Defines how to load a user
        
        This is used when calling `flask_login.current_user`
        
        In this case, we get User by ID
        '''
        return user_model.query.get(uid)


def locale(app):
    '''
    Initialize a locale for the current request

    Params:
        app: Flask application instance
    
    Returns: str
    '''
    
    @babel.localeselector
    def get_locale():
        
        # If user is logged in, use the user's current locale setting
        if current_user.is_authenticated:
            return current_user.locale

        # Try to get the language from the session (this has to have been set by the user before)
        try:
            language = session['language']
        except KeyError:
            language = None
        
        if language is not None:
            return language
        
        # Try to determine best language using HTTP headers
        accept_languages = app.config.get('LANGUAGES').keys()
        return request.accept_languages.best_match(accept_languages)
    
    @app.context_processor
    def inject_conf_var():
        '''Make these variables available to all templates'''
        
        accept_languages = app.config.get('LANGUAGES').keys()
        
        return dict(
            LANGUAGES=app.config['LANGUAGES'],
            CURRENT_LANGUAGE=session.get('language', request.accept_languages.best_match(accept_languages))
        )


def middleware(app):
    '''
    Register 0 or more middleware (mutates the app passed in)

    This lives beween WSGI and Flask, and allows us to augment WSGI data before it reaches Flask 

    Params:
        app: Flask application instance
    '''
    
    # Swap `request.remote_addr` with the real IP address even if it's behind a proxy
    app.wsgi_app = ProxyFix(app.wsgi_app)


def error_templates(app):
    '''
    Register 0 or more custom error pages (mutates the app passed in)

    Params:
        app: Flask application instance
    '''
    
    def render_status(status):
        '''
         Render a custom template for a specific status code

         Source: http://stackoverflow.com/a/30108946

         Params:
            status (str): Status as a written name
         '''
         
        # Get the status code from the status, default to a 500 so that we catch all types of errors and treat them as a 500
        code = getattr(status, 'code', 500)
        
        # Render custom error page
        return render_template('errors/{}.html'.format(code)), code

    # Associate each error code to their template
    for error in [404, 500]:
        app.errorhandler(error)(render_status)
    

def exception_handler(app):
    '''
    Register 0 or more exception handlers (mutates the app passed in)
    
    Note: Error emails are only sent when `DEBUG = False`

    Params:
        app: Flask application instance
    '''
    
    # Email errors to admins 
    mail_handler = SMTPHandler(
        mailhost=(
            app.config.get('MAIL_HOSTNAME'), 
            app.config.get('MAIL_PORT') 
        ),
        fromaddr=app.config.get('MAIL_EMAIL'),
        toaddrs=[
            app.config.get('SEED_ADMIN_EMAIL')
        ],
        subject='[badmintontv.ai Exception Handler] A 5xx error was thrown',
        credentials=(
            app.config.get('MAIL_EMAIL'), 
            app.config.get('MAIL_PASSWORD')
        ),
        secure=()
    )

    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter("""
        Time:               %(asctime)s
        Message type:       %(levelname)s


        Message:

        %(message)s
        """
    ))
    
    # Add to Flask app 
    app.logger.addHandler(mail_handler)
