import datetime
import pytz

from sqlalchemy import or_
from hashlib import md5
from collections import OrderedDict
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer

from libs.util_sqlalchemy import ResourceMixin, AwareDateTime
from libs.util_datetime import tzware_datetime
from libs.util_ip import ip_to_region
from badmintontv.blueprints.billing.models.card import Card
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.view.models import View
from badmintontv.extensions import db


class User(UserMixin, ResourceMixin, db.Model):
    
    # Maps lower-case version to human-readable/upper-case version 
    # We use an ORDERED dict because we may want a drop-down box on the site in the future 
    ROLE = OrderedDict([
        ('member', 'Member'),
        ('admin', 'Admin')
    ])

    # Table name 
    __tablename__ = 'users'
    
    # Primary key INTEGER 
    id = db.Column(db.Integer, primary_key=True)
    
    
    # ---------------------------------------------
    # --------------- Relationships ---------------
    # ---------------------------------------------
    
    # [User] One (User) to One (Card) 
    card = db.relationship(
        Card, 
        uselist=False, 
        backref='users',
        passive_deletes=True
    )
    
    # [User] One (User) to One (Subscription) 
    subscription = db.relationship(
        Subscription, 
        uselist=False,         # This is NOT a list, since a user can only have 1 subscription
        backref='users',       # This is where the relationship takes place on
        passive_deletes=True   # Optimization: Don't load in related (aka `subscription`) object before deleting user
    )
    
    # [User] One (User) to Many (Invoice)
    invoices = db.relationship(
        Invoice, 
        backref='users', 
        passive_deletes=True
    )
    
    # [User] One (User) to Many (View)
    views = db.relationship(
        View, 
        backref='users', 
        passive_deletes=True
    )


    # --------------------------------------------------------------
    # --------------- Authentication-related columns ---------------
    # --------------------------------------------------------------
    
    # Distinguishes user types ('admin', 'member')
    role = db.Column(
        db.Enum(
            *ROLE, 
            name='role_types',    # Name of enum variable 
            native_enum=False     # Tells SQLAlchemy to not use the native enum implementation (can be cumbersome)
        ), 
        index=True,               # Sets up a DB index (allows the DB to look this up efficiently)
        nullable=False,           # Can't be null
        server_default='member'   # If it isn't set explicitly, defaults to 'member'
    )

    active = db.Column(
        'is_active',         # Required column name for Flask-Login
        db.Boolean(), 
        nullable=False, 
        server_default='1'   # Default to yes/true (is active)
    )
    
    username = db.Column(
        db.String(30), 
        unique=True,        # Username must be unique 
        nullable=False,     # Username is required 
        index=True
    )
    
    email = db.Column(
        db.String(255), 
        unique=True,         # Email must be unique 
        nullable=False,      # Email is required 
        index=True
    )
    
    password = db.Column(
        db.String(128), 
        nullable=False       # Password is required 
    )
    
    # Email confirmation 
    confirmed = db.Column(
        db.Boolean(),
        nullable=False,
        server_default='0'  # Default to email not confirmed
    )


    # -------------------------------------------------
    # --------------- Activity tracking ---------------
    # -------------------------------------------------
    
    # Number of times a user has signed-in
    sign_in_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Current/Last sign-in times and IP addresses
    current_sign_in_on = db.Column(AwareDateTime())
    current_sign_in_ip = db.Column(db.String(45))
    current_sign_in_region = db.Column(db.String(45))
    last_sign_in_on = db.Column(AwareDateTime())
    last_sign_in_ip = db.Column(db.String(45))
    
    
    # ----------------------------------------
    # --------------- Payments ---------------
    # ----------------------------------------
    
    # Billing name 
    name = db.Column(db.String(128), index=True)
    
    # Customer ID from Stripe (used to change user's plan)
    payment_id = db.Column(db.String(128), index=True)
    
    # When a user cancelled their subscription
    cancelled_subscription_on = db.Column(AwareDateTime())
    
    
    # ---------------------------------------------------
    # --------------- Additional settings ---------------
    # ---------------------------------------------------
    
    # Default language to english 
    locale = db.Column(
        db.String(5), 
        nullable=False, 
        server_default='en'
    )
    
    
    def __init__(self, **kwargs):
        
        # Call Flask-SQLAlchemy's constructor using all arguments 
        super(User, self).__init__(**kwargs)

        # Encrypt password ASAP 
        self.password = User.encrypt_password(kwargs.get('password', ''))

    @classmethod
    def find_by_identity(cls, identity):
        '''
        Find a user by their e-mail or username

        Params:
            identity (str): Email or username
        
        Returns: User instance
        '''
        return User.query.filter(
            (User.email == identity) | (User.username == identity)
        ).first()
        
    @classmethod
    def find_by_id(cls, id):
        '''
        Find a user by their ID

        Params:
            id (str): User ID
        
        Returns: User instance
        '''
        return User.query.filter(User.id == id).first()
    
    @classmethod
    def bulk_delete(cls, ids):
        '''
        Override the general bulk_delete method because we need to delete them
        one at a time while also deleting them on Stripe

        Params:
            ids (list): List of ids to be deleted
        
        Returns: Number of users deleted
        '''
        
        delete_count = 0

        # Loop over user IDs
        for id in ids:
            
            # Get user by ID 
            user = User.query.get(id)

            # Make sure they exist 
            if user is None:
                continue

            # If they have no payment ID (customer ID on Stripe)
            if user.payment_id is None:
                
                # Delete normally 
                user.delete()
            
            # User has a subscription
            else:
                
                # Cancel it 
                subscription = Subscription()
                cancelled = subscription.cancel(
                    user=user
                )

                # If successful, delete it locally
                if cancelled:
                    user.delete()

            # Increment count 
            delete_count += 1

        return delete_count

    @classmethod
    def encrypt_password(cls, plaintext_password):
        '''
        Hash a plaintext string using PBKDF2. This is good enough according
        to the NIST (National Institute of Standards and Technology).

        In other words while bcrypt might be superior in practice, if you use
        PBKDF2 properly (which we are), then your passwords are safe.

        Params:
            plaintext_password (str): Password in plain text
        
        Returns: Hashed password 
        '''
        
        # Hashing 
        return generate_password_hash(plaintext_password)

    def authenticated(self, password='', with_password=True):
        '''
        Ensure a user is authenticated 
    
        By default, this is achieved by comparing encrypted passwords
        
        In the case of an emergency, we can set `with_password=False`, and check any problems a user 
        may be experiencing on their account specifically

        Params:
            password (str):          Optionally verify this as their password
            with_password (bool):    Optionally check using their password
        
        Returns: True if authenticated; False otherwise 
        '''
        if with_password:
            return check_password_hash(self.password, password)

        return True
    
    def update_activity_tracking(self, ip_address):
        '''
        Update a user's metadata fields that's related to their account, specifically:
        - Sign in count 
        - Current and last sign-in IP address
        - Current and last sign-in time 

        Params:
            ip_address (str): IP address
        
        Returns: SQLAlchemy commit results
        '''
        
        # Increment number of times signed-in 
        self.sign_in_count += 1

        # Save previous sign-in info 
        self.last_sign_in_on = self.current_sign_in_on
        self.last_sign_in_ip = self.current_sign_in_ip

        # Save current sign-in info 
        self.current_sign_in_on = tzware_datetime()
        self.current_sign_in_ip = ip_address
        try:
            self.current_sign_in_region = ip_to_region(
                ip_address,
                access_token=current_app.config['IPINFO_ACCESS_TOKEN']
            )
        except:
            self.current_sign_in_region = None
        return self.save()

    @classmethod
    def initialize_signup(cls, username, email, password):
        '''
        Generates a token to sign up a new user

        Params:
            username (str):   Username user entered
            email (str):      Email user entered
            password (str):   Password user entered (not encrypted)
            
        Returns: User instance
        '''
        
        # Create a user 
        user = User(
            username=username,
            email=email,
            password=password
        )
        
        # Save DB
        user.save()
        
        # Create serialized token 
        signup_token = user.serialize_token()

        # commenting this for making a user
        # This prevents circular imports
        # from badmintontv.blueprints.user.tasks import deliver_signup_email
        
        # # Send email in background 
        # deliver_signup_email.delay(
        #     user_id=user.id, 
        #     signup_token=signup_token
        # )

        return user

    @classmethod
    def initialize_password_reset(cls, identity):
        '''
        Generates a token to reset the password for a specific user

        Params:
            identity (str): User e-mail address or username
            
        Returns: User instance
        '''
        
        # Get user by ID 
        user = User.find_by_identity(identity)
        
        # Create serialized token 
        reset_token = user.serialize_token()

        # This prevents circular imports
        from badmintontv.blueprints.user.tasks import deliver_password_reset_email
        
        # Send email in background 
        deliver_password_reset_email.delay(
            user_id=user.id, 
            reset_token=reset_token
        )

        return user
    
    def serialize_token(self, expiration=3600):
        '''
        Sign and create a token (using the secret key) that can be used for tasks 
        (such as resetting a password) that involve a one off token

        Params:
            expiration (int): Seconds until it expires; Defaults to 1 hour
            
        Returns:
            token (json): Serialized token
        '''
        
        # Get secret key 
        private_key = current_app.config['SECRET_KEY']

        # Used to create timed token 
        serializer = TimedJSONWebSignatureSerializer(private_key, expiration)
        
        # UTF-8 representation of user's email address, in JSON format
        return serializer.dumps({'user_email': self.email}).decode('utf-8') 
            
    @classmethod
    def deserialize_token(cls, token):
        '''
        Get a user from de-serializing a signed token

        Params:
            token (str): Signed token
            
        Returns: User instance if deserlization succeeded; None otherwise
        '''
        
        # Create private key using secret key 
        private_key = TimedJSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        
        try:
            
            # Decode token
            decoded_payload = private_key.loads(token)
            payload = decoded_payload.get('user_email')
            
            # Return user object
            return User.find_by_identity(payload)
        
        except Exception:
            return None

    def is_active(self):
        '''
        Returns whether or not the user account is active
        
        This satisfies `Flask-Login` by overwriting the default value
        
        Returns: True if user is active; False otherwise
        '''
        return self.active

    @classmethod
    def is_last_admin(cls, user, new_role, new_active):
        '''
        Determine whether or not this user is the last admin account

        Params:
            user (User):         User being tested 
            new_role (str):      New role being set
            new_active (bool):   New active status being set
        
        Returns: True if this user is the last admin; False otherwise
        '''
        
        # Check 1: Check if user is admin, and is changing to a non-admin 
        is_changing_roles = user.role == 'admin' and new_role != 'admin'
        
        # Check 2: Is the current user is active, and we want to de-activate it?
        is_changing_active = user.active is True and new_active is None

        # This user is either being demoted to a member, or is being de-activated 
        if is_changing_roles or is_changing_active:
            
            # Number of admin accounts 
            admin_count = User.query.filter(User.role == 'admin').count()
            
            # Number of active accounts 
            active_count = User.query.filter(User.is_active is True).count()

            # If this is either the last admin or last active account, yes, this is the last admin 
            if admin_count == 1 or active_count == 1:
                return True

        # Otherwise this is not the last admin 
        return False
    
    @classmethod
    def search(cls, query):
        '''
        Search a resource by 1 or more fields
        
        This search:
        - Supports partial-words 
        - Is case-insensitive
        - Filters through `email` and `username`

        Params:
            query (str): Search query
        
        Returns: SQLAlchemy filter
        '''
        
        # Return empty string if there's no search query
        if query == '':
            return ''

        # This tells SQLAlchemy that we want to search for partial-words 
        search_query = '%{}%'.format(query)
        
        # Search through email and usernames (`ilike` makes it case-insensitive)
        search_chain = (
            User.email.ilike(search_query),
            User.username.ilike(search_query)
        )

        # Allow matching to work on email, username, OR both  
        # Note: Alternatively, `and_` returns results on email AND username 
        return or_(*search_chain)
    
