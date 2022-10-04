from flask import current_app

from config import settings
from libs.util_sqlalchemy import ResourceMixin, AwareDateTime
from libs.util_datetime import tzware_datetime, datetime_to_utc_timestamp, utc_timestamp_to_datetime, localize_datetime, format_datetime
from badmintontv.extensions import db
from badmintontv.blueprints.billing.models.card import Card
from badmintontv.blueprints.billing.gateways.stripecom import Card as PaymentCard
from badmintontv.blueprints.billing.gateways.stripecom import Subscription as PaymentSubscription
from badmintontv.blueprints.billing.gateways.stripecom import SubscriptionSchedule as PaymentSubscriptionSchedule
from badmintontv.blueprints.billing.gateways.stripecom import Customer


class Subscription(ResourceMixin, db.Model):
    
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)


    # -----------------------------------------------
    # ---------------- Relationships ----------------
    # -----------------------------------------------
    
    # [Subscription] One (Subscription) to One (User) 
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'users.id',
            onupdate='CASCADE',   # If we delete the user, we also want the subscription to be deleted
            ondelete='CASCADE'    # Note: These could be set to 'set null', which would set the user ID field to null
        ),
        index=True,
        nullable=False     # Note: This is set to match with 'CASCADE' settings above
    )
    
    
    # -----------------------------------------
    # ---------------- Details ----------------
    # -----------------------------------------
    
    # Start/End dates for this billing cycle 
    current_period_start = db.Column(AwareDateTime())
    current_period_end = db.Column(AwareDateTime())
    
    # Plan ID
    plan_id = db.Column(db.String(128))
    
    # Th new plan ID that has been set to change in the next billing cycle
    new_plan_id = db.Column(db.String(128))
    
    # Subscription ID 
    subscription_id = db.Column(db.String(128))
    
    # Subscription Schedule ID
    subscription_schedule_id = db.Column(db.String(128))
    

    def __init__(self, **kwargs):
    
        # Call Flask-SQLAlchemy's constructor
        super(Subscription, self).__init__(**kwargs)

    @classmethod
    def get_plan_by_id(cls, id):
        '''
        Returns information about a plan, given its ID

        Params:
            id (str): ID to identify plan 
            
        Returns: Dict or None
        '''
        for key, value in settings.STRIPE_PRICES.items():
            if value['id'] == id:
                return settings.STRIPE_PRICES[key]
    
    @classmethod
    def get_plan_by_subscription_id(cls, id):
        '''
        Returns information about a plan, given its subscription ID

        Params:
            id (str): Subscription ID
            
        Returns: 
            subscription (Subscription)
        '''
        return Subscription.query.filter(
            (Subscription.subscription_id == id)
        ).first()
    
    def delete_subscription(cls, id):
        '''
        Delete a subscription by ID
        
        Params:
            id (str): Subscription ID
        
        Returns: 
            True if the subsciption was deleted; False otherwise 
        '''
        
        subscription = cls.get_plan_by_id(id)
        
        return subscription.delete()
        
    @classmethod
    def get_new_plan(cls, keys):
        '''
        Pick the plan based on the plan identifier

        Params:
            keys (list): Keys to look through
        
        Returns: Plan ID to return or None
        '''
        
        # Loop over keys 
        for key in keys:
            
            # Remove 'submit_' from key (this is the first part of the button name)
            split_key = key.split('submit_')

            # Safety check for format
            if isinstance(split_key, list) and len(split_key) == 2:
                
                # If this plan ID is legit, return plan ID
                if Subscription.get_plan_by_id(split_key[1]):
                    return split_key[1]

    def create(self, user, name, id, token):
        '''
        Create a recurring subscription

        Params:
            user (User):  User to apply the subscription to
            name (str):   User's billing name
            id (str):     Plan ID
            token (str):  Token returned by the JS
        
        Returns: True if subscription was successfully created; False otherwise
        '''
        
        # Pre-emptively fail without creating Stripe, since without a token it's for sure to fail 
        if token is None:
            return False
        
        # [Stripe] Customer doesn't exist 
        has_customer_id = user.payment_id
        if not has_customer_id:
            
            # [STRIPE, DEBUG] Use test clock?
            if current_app.config['DEBUG'] and current_app.config['STRIPE_TEST_CLOCK']:
                test_clock = current_app.config['STRIPE_TEST_CLOCK']
                current_app.logger.debug('[Stripe] Using test clock {}'.format(test_clock))
            else:
                test_clock = None

            # [Stripe] Create customer + card
            customer = Customer.create(
                name=name,
                email=user.email,
                token=token,
                test_clock=test_clock
            )
            customer_id = customer.id
            current_app.logger.debug('[Stripe] {} new customer ID created {}'.format(
                user.username, 
                customer_id
            ))

        # Customer does exist
        else:
            
            # Use same customer
            customer_id = user.payment_id 
            customer = Customer.retrieve(customer_id=customer_id)
            
            # Create new default card 
            PaymentCard.update(
                customer_id=customer_id,
                name=name,
                token=token
            )
            
            # Get new customer 
            customer = Customer.retrieve(customer_id=customer_id)
        
        # [Stripe] Create subsciption
        subscription = PaymentSubscription.create(
            customer_id=customer_id,
            plan_id=id
        )
        current_app.logger.debug('[Stripe] Created subscription {}'.format(subscription.id))
        
        # [DB] Create subscription 
        self.user_id = user.id
        self.plan_id = id
        self.new_plan_id = id
        self.subscription_id = subscription.id
                
        
        # ----------------------------------------------------------------
        # ----------- Saving start/end dates in correct format -----------
        # ----------------------------------------------------------------
        
        # Timestamp 
        current_period_start = subscription['current_period_start']
        current_period_end = subscription['current_period_end']
        
        # Timestamp --> unaware `datetime`
        current_period_start_datetime = utc_timestamp_to_datetime(current_period_start)
        current_period_end_datetime = utc_timestamp_to_datetime(current_period_end)
        
        # unaware `datetime` --> aware `datetime`
        current_period_start_datetime_utc = localize_datetime(current_period_start_datetime)
        current_period_end_datetime_utc = localize_datetime(current_period_end_datetime)
        
        # Save 
        self.current_period_start = current_period_start_datetime_utc
        self.current_period_end = current_period_end_datetime_utc
        
        current_app.logger.debug('[DB] Created subscription')

        # ----------------------------------------------------------------


        # [DB] Update user
        user.payment_id = customer_id    # Assign Stripe's customer ID to our User payment ID
        user.name = name
        user.cancelled_subscription_on = None    # Reset cancelled subscription date
        current_app.logger.debug('[DB] Updated user')
        
        # [DB] Create card
        card = Card(
            user_id=user.id,
            **Card.extract_card_params(customer)   # Get card parameters from the Stripe object
        )
        current_app.logger.debug('[DB] Created card')

        # [DB] Save user, card, and subscription 
        db.session.add(user)
        db.session.add(card)
        db.session.add(self)
        
        db.session.commit()

        # Success
        return True

    def update(self, user, plan_id):
        '''
        Update an existing subscription

        Params:
            user (User):    User to apply the subscription to
            plan_id (str):  ID of plan to update to 
            
        Returns: True if subscription was successfully updated; False otherwise
        '''
        
        # Logs 
        plan_name = configs.STRIPE_PRICES[plan_id]['name']
        old_plan_name = configs.STRIPE_PRICES[user.subscription.plan_id]['name']
        current_app.logger.debug('Changing plans {} --> {}'.format(old_plan_name, plan_name))

        # aware `datetime` --> timestamp
        current_period_start_datetime = user.subscription.current_period_start
        current_period_start = datetime_to_utc_timestamp(current_period_start_datetime)
        
        current_period_end_datetime = user.subscription.current_period_end
        current_period_end = datetime_to_utc_timestamp(current_period_end_datetime)
        
        current_app.logger.debug('Setting schedule to:\n\tPhase 1:\n\t\t{:<7} {}\n\t\t{:<7} {}\n\tPhase 2:\n\t\t{:<7} {}'.format(
            'Start:',
            format_datetime(current_period_start_datetime), 
            'End:',
            format_datetime(current_period_end_datetime),
            'Start:',
            format_datetime(current_period_end_datetime)            
        ))
        
        # [Stripe] Update subscription 
        subscription_schedule = PaymentSubscriptionSchedule.update(
            customer_id=user.payment_id,
            subscription_schedule_id=user.subscription.subscription_schedule_id,
            plan_id=plan_id,
            old_plan_id=user.subscription.plan_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        # [Logs] No previous subscription schedule 
        if not user.subscription.subscription_schedule_id:
            current_app.logger.debug('[Stripe] Created subscription schedule {}'.format(subscription_schedule.id))
        # [Logs] Changing subscription schedule 
        else:
            current_app.logger.debug('[Stripe] Updated subscription schedule {}'.format(subscription_schedule.id))

        # [DB] Update subsciption details 
        user.subscription.new_plan_id = plan_id
        user.subscription.subscription_schedule_id = subscription_schedule.id
        current_app.logger.debug('[DB] Updated subscription')
        
        # [DB] Save
        db.session.add(user.subscription)
        db.session.commit()

        # Success
        return True

    @classmethod
    def cancel(cls, user):
        '''
        Cancel an existing subscription

        Params:
            user (User): User to apply the subscription to
        
        Returns: True if subscription was successfully cancelled; False otherwise
        '''
        
        # [Stripe] Cancel subscription
        subscription = PaymentSubscription.cancel(
            customer_id=user.payment_id
        )
        current_app.logger.debug('[Stripe] Cancelled subscription {}'.format(subscription.id))

        # [DB] Update user 
        user.cancelled_subscription_on = tzware_datetime()
        current_app.logger.debug('[DB] Updated user {}'.format(user.username))

        # [DB] Save user changes
        db.session.add(user)
        
        # [DB] Delete subscription
        current_app.logger.debug('[DB] Deleted subscription {}'.format(user.subscription.subscription_id))
        db.session.delete(user.subscription)

        # By default, delete the card because the foreign-key is on the 
        # user, not subscription so we can't depend on cascading deletes
        # Note: This is used in cases where you may want to keep a user's card on file even if they cancelled
        db.session.delete(user.card)

        db.session.commit()

        # Success
        return True

    def update_payment_method(self, user, card, name, token):
        '''
        Update the subscription

        Params:
            user (User):   User to modify
            card (Card):   Card to modify
            name (str):    User's billing name
            token (str):   Token returned by JavaScript
        
        Returns: True if card was successfully updated; False otherwise
        '''
        
        # Pre-emptively fail without creating Stripe, since without a token it's for sure to fail 
        if token is None:
            return False

        # [Stripe] Update card
        PaymentCard.update(
            customer_id=user.payment_id, 
            name=name,
            token=token
        )
        current_app.logger.debug('[Stripe] New card ID: {}'.format(card.id))
        
        # [DB] Update user 
        user.name = name
        current_app.logger.debug('[DB] Updated user {}'.format(user.username))

        # [Stripe] Get customer
        customer = Customer.retrieve(
            customer_id=user.payment_id
        )
        current_app.logger.debug('[Stripe] Retrieved customer {}'.format(customer.id))

        # [Stripe] Extract new card info 
        new_card = Card.extract_card_params(customer)
        current_app.logger.debug('[Stripe] Extracted card parameters'.format())
        
        # [DB] Update card
        card.brand = new_card.get('brand')
        card.last4 = new_card.get('last4')
        card.exp_date = new_card.get('exp_date')
        card.is_expiring = new_card.get('is_expiring')
        current_app.logger.debug('[DB] Updated card')

        # Save changes
        db.session.add(user)
        db.session.add(card)

        db.session.commit()

        # Success
        return True
