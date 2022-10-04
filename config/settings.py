import os 

from os.path import dirname, abspath
from datetime import timedelta
from celery.schedules import crontab


DEBUG = True
DEBUG_TB_INTERCEPT_REDIRECTS = True
LOG_LEVEL = 'DEBUG'      # CRITICAL / ERROR / WARNING / INFO / DEBUG

SERVER_NAME = 'localhost:5000'

SECRET_KEY = 'secretkey'

# Languages 
LANGUAGES = {
    'en': 'English',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean'
}
BABEL_DEFAULT_LOCALE = 'en'

# Celery
password = 'devpassword'
hostname = 'redis'
port = '6379'

# docker-compose automatically created a network using <hostname>, so services can communicate with each other 
CELERY_BROKER_URL = 'redis://:{}@{}:{}/0'.format(password, hostname, port)
CELERY_RESULT_BACKEND = 'redis://:{}@{}:{}/0'.format(password, hostname, port)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_REDIS_MAX_CONNECTIONS = 5

# Run these tasks on a set schedule
CELERYBEAT_SCHEDULE = {
    'mark-soon-to-expire-credit-cards': {                                        # Name
        'task': 'badmintontv.blueprints.billing.tasks.mark_old_credit_cards',    # Task: Mark credit cards that are going to expire soon, or have expired
        'schedule': crontab(hour=0, minute=0)                                    # Schedule: Every day at midnight)
    }
}

# Postgres
hostname = 'localhost'
port = '5432'
db_name = 'badmintontv'

# Username and password must match the ones in `.env`
username = 'postgres'
password = 'opan123'

SQLALCHEMY_DATABASE_URI = 'postgresql://{}:{}@{}:{}/{}'.format(username, password, hostname, port, db_name)

'''
Flask-SQLAlchemy was tracking object changes, but not committed to the DB, which takes resources
SQLAlchemy's in-house has a better modification tracker
So, we turn off Flask-SQLAlchemy's tracker
'''
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Initial admin user 
SEED_ADMIN_USERNAME = 'faiz'
SEED_ADMIN_EMAIL = 'faiz@gmail.com'
SEED_ADMIN_PASSWORD = 'adminpassword'

# Initial member user 
SEED_MEMBER_USERNAME = ''
SEED_MEMBER_EMAIL = ''
SEED_MEMBER_PASSWORD = 'member1password'

# Initial second member user 
SEED_MEMBER_2_USERNAME = ''
SEED_MEMBER_2_EMAIL = ''
SEED_MEMBER_2_PASSWORD = 'member2password'

# Flask-Login: Set cookies to last 90 days by default 
REMEMBER_COOKIE_DURATION = timedelta(days=90)

# Emails 
MAILGUN_API_KEY = ''
MAILGUN_DOMAIN = ''

# Payments
STRIPE_API_VERSION = '2020-08-27'
STRIPE_TEST_CLOCK = ''

STRIPE_PRODUCTS = {
    'premium_subscription_v1': {
        'id': 'premium_subscription_v1',
        'name': 'Premium Subscription v1',
        'statement_descriptor': 'badmintontv plan'
    }
}

STRIPE_CURRENCY = 'usd'
STRIPE_INTERVAL = 1
STRIPE_PRICES = {
    'price_1LXLT4B3IubKswtTh7IvUVHy': {
        'id': 'price_1LXLT4B3IubKswtTh7IvUVHy',    # This needs to be copy-pasted from Stripe after creation 
        'product': 'premium_subscription_v1',
        'name': 'Monthly',
        'amount': 245,
        'currency': STRIPE_CURRENCY,
        'billing_scheme': 'per_unit',
        'recurring': {
            'interval': 'month',
            'interval_count': STRIPE_INTERVAL
        },
        'metadata': {}
    },
    'price_1LXLT5B3IubKswtTIAptNAjR': {
        'id': 'price_1LXLT5B3IubKswtTIAptNAjR',    # This needs to be copy-pasted from Stripe after creation 
        'product': 'premium_subscription_v1',
        'name': 'Yearly',
        'amount': 2495,
        'currency': STRIPE_CURRENCY,
        'billing_scheme': 'per_unit',
        'recurring': {
            'interval': 'year',
            'interval_count': STRIPE_INTERVAL
        },
        'metadata': {
            'recommended': True
        }
    }
}

# Email for production error logs 
MAIL_HOSTNAME = 'smtp.mailgun.org'
MAIL_PORT = 587

# Videos 
config_settings_dir = dirname(abspath(__file__))  # /badmintontv/config
VID_DIR = os.path.join('/badmintontv', 'highlights')  # /badmintontv/highlights

METADATA_RUN_FILENAME = 'metadata_run.json'
METADATA_MATCH_FILENAME = 'metadata_match.json'
