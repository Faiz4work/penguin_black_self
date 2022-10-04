import stripe


class Event(object):
    
    @classmethod
    def retrieve(cls, event_id):
        '''
        Retrieve an event
        
        This is used to validate the event (by ID) in attempt to
        protect us from potentially malicious events not sent from Stripe

        Params: 
            event_id (int): Stripe event id

        Returns: Stripe event
        '''
        return stripe.Event.retrieve(event_id)


class Customer(object):
    
    @classmethod
    def create(cls, name, email, token, test_clock=None):
        '''
        Create a customer 
        
        Params:
            name (str):         Billing name
            email (str):        Email 
            token (str):        Token from JS for card information
            test_clock (str):   ID of test clock 
            
        Returns:
            customer (Stripe Customer)
        '''
        
        # Set extra params for test clock 
        if test_clock:
            test_params = {
                'test_clock': test_clock
            }
        else:
            test_params = {}
        
        customer = stripe.Customer.create(
            name=name,
            email=email,
            source=token,
            **test_params
        )
        
        return customer 
    
    @classmethod
    def retrieve(cls, customer_id):
        '''
        Retrieves a customer 
        
        Params:
            customer_id (str)
            
        Returns:
            customer (Stripe Customer)
        '''
        
        customer = stripe.Customer.retrieve(customer_id)
        
        return customer


class Card(object):

    @classmethod
    def get(cls, customer):
        '''
        Retrieves a customer's default credit card details
        
        Params:
            customer (Stripe Customer object)
        
        Returns: 
            card (Stripe Card)
        '''
        
        # Customer ID 
        customer_id = customer.id
        
        # ID of default card
        card_id = customer.default_source
        
        # Extract card data 
        card = stripe.Customer.retrieve_source(
            customer_id,
            card_id,
        )
        
        return card
    
    @classmethod
    def update(cls, customer_id, name, token):
        '''
        Update an existing card through a customer
        
        Params:
            customer_id (str):  Stripe customer id
            name (str):         Billing name 
            token (str):        Token returned by JS
        
        Returns: 
            card (Stripe Card)
        '''
        
        # Create new card
        card = stripe.Customer.create_source(
            customer_id,
            source=token,
        )
        
        # Set as new default card, and edit name 
        customer = stripe.Customer.modify(
            customer_id,
            name=name,
            default_source=card.id
        )

        return card


class Invoice(object):
    
    @classmethod
    def upcoming(cls, customer_id):
        '''
        Retrieve an upcoming invoice item for a user

        Params:
            customer_id (int): Stripe customer id
        
        Returns: 
            upcoming_invoice (Stripe Invoice object): Next invoice
        '''
        
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=customer_id
        )
        
        return upcoming_invoice


class Subscription(object):
    
    @classmethod
    def create(cls, customer_id, plan_id):
        '''
        Create a new subscription

        Params:
            customer_id (str):  Customer ID on Stripe
            plan_id (str):      Plan/Price identifier
        
        Returns: 
            subscription (Stripe Subscription)
        '''

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[
                {'price': plan_id}
            ]
        )
        
        return subscription
        
    @classmethod
    def retrieve(cls, customer_id):
        '''
        Retrieve the first subscription from a customer 
        
        Params:
            customer_id (str)
            
        Returns:
            subscription (Stripe Subscription)
            subscription_id (str)
        '''
        
        # Get all subscriptions 
        subscription = stripe.Subscription.list(
            customer=customer_id
        )
        
        # Get first subscription ID 
        subscription_id = subscription['data'][0]['id']
        
        return subscription, subscription_id

    @classmethod
    def cancel(cls, customer_id=None):
        '''
        Cancel an existing subscription

        Params:
            customer_id (int): Stripe customer ID
        
        Returns: 
            subsciption (Stripe Subscription)
        '''
        
        # Get subsciption ID by customer ID 
        _, subscription_id = cls.retrieve(customer_id)

        # Delete subscription
        subscription = stripe.Subscription.delete(subscription_id)

        return subscription


class SubscriptionSchedule(object):
    
    @classmethod
    def create(cls, subscription_id):
        '''
        Create a subscription schedule for an existing subscription
        
        Params:
            subscription_id (str): Subscription ID to create a schedule for 
        
        Returns: 
            subscription_schedule (Stripe SubscriptionSchedule)
        '''
        
        subscription_schedule = stripe.SubscriptionSchedule.create(
            from_subscription=subscription_id,
        )
        
        return subscription_schedule
    
    @classmethod
    def update(cls, customer_id, subscription_schedule_id, plan_id, old_plan_id, current_period_start, current_period_end):
        '''
        Update an existing subscription schedule
        
        Params:
            customer_id (str):                       Customer ID
            subscription_schedule_id (str or None):  Current subscription schedule ID 
            plan_id (str):                           New plan ID
            old_plan_id (str):                       Current plan ID
            current_period_start (int):              Timestamp of start of this billing period
            current_period_end (int):                Timestamp of end of this billing period

        Returns: 
            subscription_schedule (Stripe SubscriptionSchedule)
        '''
        
        subscription, subscription_id = Subscription.retrieve(customer_id)
        
        # Create a subscription schedule if one doesn't already exist 
        if not subscription_schedule_id:
            
            subscription_schedule = cls.create(
                subscription_id=subscription_id
            )
            
            subscription_schedule_id = subscription_schedule.id
            
        # Set-up changes for subsciption
        subscription_schedule = stripe.SubscriptionSchedule.modify(
            subscription_schedule_id,
            proration_behavior='none',  # Bill the full pice 
            end_behavior='release',     # Allow subscription to keep running after 
            phases=[
            
                # Continue this plan until the end of the billing cycle 
                {
                    'items': [
                        {'price': old_plan_id}
                    ],
                    'start_date': current_period_start,
                    'end_date': current_period_end,
                },
                
                # Start new plan at the end of this billing cycle 
                {
                    'items': [
                        {'price': plan_id}
                    ],
                    'start_date': current_period_end
                }
            ]
        )
        
        return subscription_schedule
    
    @classmethod
    def release(cls, subscription_schedule_id):
        '''
        Release a subsciption schedule from its attached subscription
        
        Params:
            subscription_schedule_id (str)
            
        Returns:
            subscription_schedule (Stripe SubscriptionSchedule)
        '''
        
        subscription_schedule = stripe.SubscriptionSchedule.release(
            subscription_schedule_id
        )
        
        return subscription_schedule


class Product(object):
    
    @classmethod
    def create(cls, id, name, statement_descriptor):
        '''
        Creates a product
        
        Params:
            id (str): Product ID 
            ...
        '''
        stripe.Product.create(
            id=id,
            name=name,
            statement_descriptor=statement_descriptor
        )
    
    @classmethod
    def retrieve(cls, id):
        '''
        Retrieves a product
        
        Params:
            id (str): Product ID 
        '''
        try:
            return stripe.Product.retrieve(id)
        except:
            return False

    @classmethod
    def update(cls, id, name, statement_descriptor):
        '''
        Updates a product
        
        Params:
            ...
        '''
        stripe.Product.modify(
            id,
            name=name,
            statement_descriptor=statement_descriptor
        )
        
    @classmethod
    def list(cls):
        '''...'''
        return stripe.Product.list(
            active=True
        )


class Price(object):
    
    @classmethod
    def create(cls, product, nickname, unit_amount, currency, billing_scheme, recurring):
        '''
        Creates a price for a specific product
        
        Params:
            ...
        '''
        stripe.Price.create(
            product=product,
            nickname=nickname,
            unit_amount=unit_amount,
            currency=currency,
            billing_scheme=billing_scheme,
            recurring=recurring
        )
    
    @classmethod
    def retrieve(cls, id):
        try:
            return stripe.Price.retrieve(id)
        except:
            return False
        
    @classmethod
    def list(cls, product):
        return stripe.Price.list(
            product=product,
            active=True
        )


class TestClock(object):
    
    @classmethod
    def create(cls, frozen_time, name):
        '''
        Create a Test Clock 
        
        Params:
            frozen_time (str):   UTC Starting Timestamp
            name (str):          Name of clock 
        '''
        return stripe.test_helpers.TestClock.create(
            frozen_time=frozen_time,
            name=name
        )
        
    @classmethod
    def list(cls):
        '''Lists all Test Clocks'''
        return stripe.test_helpers.TestClock.list()
