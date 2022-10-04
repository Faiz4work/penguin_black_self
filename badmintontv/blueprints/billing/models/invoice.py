from sqlalchemy import or_

from config import settings
from libs.util_sqlalchemy import ResourceMixin
from libs.util_datetime import utc_timestamp_to_datetime
from badmintontv.extensions import db
from badmintontv.blueprints.billing.gateways.stripecom import Invoice as PaymentInvoice


class Invoice(ResourceMixin, db.Model):
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)


    # -----------------------------------------------------
    # ------------------- Relationships -------------------
    # -----------------------------------------------------
    
    # [Invoice] One (Invoice) to One (User)
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


    # -----------------------------------
    # --------- Payment details ---------
    # -----------------------------------
    
    download_url = db.Column(db.String(512), index=True)
    invoice_number = db.Column(db.String(128), index=True)
    receipt_number = db.Column(db.String(128), index=True)


    # ----------------------------------
    # ---------- Plan details ----------
    # ----------------------------------
    
    plan_id = db.Column(db.String(128), index=True)
    plan_name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    period_start_on = db.Column(db.Date)
    period_end_on = db.Column(db.Date)
    currency = db.Column(db.String(8))
    total = db.Column(db.Integer())


    # --------------------------------
    # --------- Card details ---------
    # --------------------------------
    
    # De-normalize (keep a copy of the data in a different table) the card details 
    # so we can render a user's history properly even if they have 
    # no active subscription or changed cards at some point
    
    brand = db.Column(db.String(32))
    last4 = db.Column(db.Integer)
    exp_date = db.Column(db.Date, index=True)
    

    def __init__(self, **kwargs):
        
        # Call Flask-SQLAlchemy's constructor
        super(Invoice, self).__init__(**kwargs)

    @classmethod
    def upcoming(cls, customer_id):
        '''
        Return the upcoming invoice item

        Params: 
            customer_id (int): Stripe customer id
        
        Returns: 
            invoice_formatted (dict): Formatted Stripe Invoice 
        '''
        
        # Get invoice from Sripe
        invoice = PaymentInvoice.upcoming(
            customer_id=customer_id
        )

        # Format 
        invoice_formatted = Invoice.parse_from_api(
            payload=invoice
        )

        return invoice_formatted
        
    @classmethod
    def billing_history(cls, user=None, num_recent=12):
        '''
        Return the billing history for a specific user

        Params:
            user (User):        User whose billing history will be retrieved
            num_recent (int):   Number of most recent invoices to retrieve

        Returns: Invoices
        '''
        
        invoices = Invoice.query.filter(
            # Get invoices for this user 
            Invoice.user_id == user.id
        ).order_by(
            # Sort descending by creation date, return only latest `num_recent` invoices
        Invoice.created_on.desc()).limit(num_recent)

        return invoices
        
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
        
        # Prevent circular imports 
        from badmintontv.blueprints.user.models import User

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


    @classmethod
    def parse_from_event(cls, payload):
        '''
        Extract relevant invoice information 

        Params:
            payload (Stripe Invoice)

        Returns: 
            invoice (dict): Invoice information
        '''
        
        data = payload['data']['object']        
        plan_info = data['lines']['data'][0]['plan']

        period_start_on = data['lines']['data'][0]['period']['start']
        period_start_on = utc_timestamp_to_datetime(period_start_on).date()
        
        period_end_on = data['lines']['data'][0]['period']['end']
        period_end_on = utc_timestamp_to_datetime(period_end_on).date()

        # Get product description
        description = ''
        for key, value in settings.STRIPE_PRICES.items():
            if value['id'] == plan_info['id']:
                product_id = value['product']
                description = settings.STRIPE_PRODUCTS[product_id]['statement_descriptor']

        # Get plan ID and name 
        plan_id = plan_info['id']
        plan_name = settings.STRIPE_PRICES[plan_id]['name']

        invoice = {
            'payment_id': data['customer'],  # Used to retrieve card information (will be removed later)
            
            # Payment details 
            'download_url': data['hosted_invoice_url'],  # Link to download invoice/receipt
            'invoice_number': data['number'],
            'receipt_number': data['receipt_number'],
            
            # Plan details 
            'plan_id': plan_id,
            'plan_name': plan_name,
            'description': description,
            'period_start_on': period_start_on,
            'period_end_on': period_end_on,
            'currency': data['currency'],
            'total': data['total']
        }

        return invoice

    @classmethod
    def parse_from_api(cls, payload):
        '''
        Parse and return the invoice information we are interested in

        Params:
            payload (Invoice): Stripe invoice

        Returns: Dictionary of relevant invoice information
        '''
        
        # Plan information 
        plan_info = payload['lines']['data'][0]['plan']
        
        # Next attempted billing date 
        date = utc_timestamp_to_datetime(payload['next_payment_attempt'])

        # Get plan name
        name = ''
        for key, value in settings.STRIPE_PRICES.items():
            if value.get('id') == plan_info['id']:
                name = value.get('name')
        
        # Set-up parameters 
        invoice = {
            'plan': name,
            'next_bill_on': date,
            'amount_due': payload['amount_due'],
        }

        return invoice

    @classmethod
    def prepare_and_save(cls, parsed_event):
        '''
        Potentially save the invoice after parsing the Invoice from Stripe

        Params:
            parsed_event (dict): Event parameters to be saved
        
        Returns: User instance
        '''
        
        # Avoid circular imports
        from badmintontv.blueprints.user.models import User

        # Only save the invoice if the user's payment ID is valid, AND they have a credit card
        id = parsed_event.get('payment_id')
        user = User.query.filter((User.payment_id == id)).first()
        if user and user.card:
            
            # Add user info 
            parsed_event['user_id'] = user.id
            
            # Add card info 
            parsed_event['brand'] = user.card.brand
            parsed_event['last4'] = user.card.last4
            parsed_event['exp_date'] = user.card.exp_date

            # Delete this key 
            del parsed_event['payment_id']

            # Save new invoice 
            invoice = Invoice(**parsed_event)
            invoice.save()

        return user
