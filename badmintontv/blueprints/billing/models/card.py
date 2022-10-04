import datetime

from libs.util_datetime import timedelta_months
from libs.util_sqlalchemy import ResourceMixin
from badmintontv.extensions import db
from badmintontv.blueprints.billing.gateways.stripecom import Card as PaymentCard


class Card(ResourceMixin, db.Model):
    
    # Threshold (in months), to give a site-wide notice to update an expiring card 
    IS_EXPIRING_THRESHOLD_MONTHS = 2

    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)


    # -----------------------------------------------
    # ---------------- Relationships ----------------
    # -----------------------------------------------
    
    # [Card] One (Card) to One (User) 
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey(
            'users.id',
            onupdate='CASCADE',
            ondelete='CASCADE'
        ),
        index=True, 
        nullable=False
    )


    # -----------------------------------------
    # ---------------- Details ----------------
    # -----------------------------------------
    
    # Brand of the card
    brand = db.Column(db.String(32))
    
    # Last 4 digits 
    last4 = db.Column(db.Integer)
    
    # Expiration date 
    exp_date = db.Column(db.Date, index=True)
    
    # Will the card expire soon?
    is_expiring = db.Column(
        db.Boolean(), 
        nullable=False, 
        server_default='0'    # Default to 'No'
    )

    def __init__(self, **kwargs):
        
        # Call Flask-SQLAlchemy's constructor
        super(Card, self).__init__(**kwargs)

    @classmethod
    def is_expiring_soon(cls, compare_date=None, expiration_date=None):
        '''
        Determines whether or not this credit card is expiring soon

        Params:
            compare_date (date):      Date to compare with `IS_EXPIRING_THRESHOLD_MONTHS`
            expiration_date (date):   Expiration date
        
        Returns: True if the card will expire soon; False otherwise 
        '''
        return expiration_date <= timedelta_months(
            months=Card.IS_EXPIRING_THRESHOLD_MONTHS, 
            compare_date=compare_date
        )

    @classmethod
    def mark_old_credit_cards(cls, compare_date=None):
        '''
        Mark credit cards that:
        - Are going to expire soon, or 
        - Have expired

        Params:
            compare_date (date): Date to compare to
            
        Returns: Result of updating the records
        '''
        
        # Get today's date (since we won't pass a `compare_date` parameter) with the delta threshold applied
        today_with_delta = timedelta_months(
            months=Card.IS_EXPIRING_THRESHOLD_MONTHS, 
            compare_date=compare_date
        )

        # Get all cards that are about to expire 
        Card.query.filter(
            # Compare each card's expiration date with today's date with the delta applied 
            Card.exp_date <= today_with_delta
        ).update(
            # Update these cards' `is_expiring` fields 
            { Card.is_expiring: True }
        )
        
        # Save changes
        return db.session.commit()

    @classmethod
    def extract_card_params(cls, customer):
        '''
        Extract the credit card info from a Stripe payment customer object
        
        This is used when:
        - A user creates a new subscription, and 
        - A user updates their payment information

        Params:
            customer (Stripe payment customer): Payment customer
        
        Returns: Dictionary of credit card information 
        '''
        
        # [Stripe] Get credit card
        card_data = PaymentCard.get(customer)
        
        # Build-up expiration date (1st day of that year-month)
        exp_date = datetime.date(
            card_data.exp_year, 
            card_data.exp_month, 
            1
        )

        card = {
            'brand': card_data.brand,
            'last4': card_data.last4,
            'exp_date': exp_date,
            'is_expiring': Card.is_expiring_soon(expiration_date=exp_date)    # Check if card is expiring "soon"
        }
        return card
