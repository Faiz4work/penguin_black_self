from flask import Blueprint, request, current_app
from stripe.error import InvalidRequestError

from libs.util_json import render_json
from libs.util_datetime import localize_datetime, utc_timestamp_to_datetime, format_datetime
from badmintontv.extensions import csrf
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.billing.gateways.stripecom import Event as PaymentEvent
from badmintontv.blueprints.billing.gateways.stripecom import SubscriptionSchedule as PaymentSubscriptionSchedule

stripe_webhook = Blueprint(
    'stripe_webhook', 
    __name__,
    url_prefix='/stripe_webhook'
)


@stripe_webhook.route('/invoice_payment_succeeded', methods=['POST'])
@csrf.exempt    # Allow this endpoint to not contain a CSRF token 
def invoice_payment_succeeded():
    '''
    Event: invoice.payment_succeeded
    
    Action: Save the new invoice to the DB
    '''
    
    # Make sure we have a JSON request 
    if not request.json:
        return render_json(406, {'error': 'Mime-type is not application/json'})

    # Make sure it has an `id` field
    if request.json.get('id') is None:
        return render_json(406, {'error': 'Invalid Stripe event'})

    try:
        
        # Retrieve legit event from Stripe 
        safe_event = PaymentEvent.retrieve(
            event_id=request.json.get('id')
        )
        
        # Format
        parsed_event = Invoice.parse_from_event(safe_event)

        # Save invoice in DB
        Invoice.prepare_and_save(parsed_event)
    
    # We could not parse the event
    except InvalidRequestError as e:
        
        return render_json(422, {'error': str(e)})
    
    # Return a 200 because something is really wrong and we want Stripe to stop trying to fulfill this webhook request
    except Exception as e:
        return render_json(200, {'error': str(e)})

    # Success
    return render_json(200, {'success': True})


@stripe_webhook.route('/invoice_payment_failed', methods=['POST'])
@csrf.exempt
def invoice_payment_failed():
    '''
    Event: invoice.payment_failed
    
    Action: Delete user's subscription
    '''
    
    # Make sure we have a JSON request 
    if not request.json:
        return render_json(406, {'error': 'Mime-type is not application/json'})

    # Make sure it has an `id` field
    if request.json.get('id') is None:
        return render_json(406, {'error': 'Invalid Stripe event'})

    try:
        
        # Retrieve legit event from Stripe 
        safe_event = PaymentEvent.retrieve(
            event_id=request.json.get('id')
        )
        
        # Get subscription_id
        data = safe_event['data']['object']        
        subscription_id = data['subscription']
        
        # Get subscription and associated user 
        subscription = Subscription.get_plan_by_subscription_id(subscription_id)
        user_id = subscription.user_id
        user = User.find_by_id(user_id)
        
        # Delete subscription
        subscription_deleted = Subscription.cancel(
            user=user
        )
        
    # We could not parse the event
    except InvalidRequestError as e:
        
        return render_json(422, {'error': str(e)})
    
    # Return a 200 because something is really wrong and we want Stripe to stop trying to fulfill this webhook request
    except Exception as e:
        return render_json(200, {'error': str(e)})

    # Success
    return render_json(200, {'success': True})


@stripe_webhook.route('/subscription_updated', methods=['POST'])
@csrf.exempt
def subscription_updated():
    '''
    Event: customer.subscription.updated
    
    Actions: Potentially update the subscription to prepare for the next billing cycle and release subscription schedule
    
    `Subscription` values being update:
    - plan_id
    - subscription_schedule_id
    - current_period_start
    - current_period_end
    '''
    
    # Make sure we have a JSON request 
    if not request.json:
        return render_json(406, {'error': 'Mime-type is not application/json'})

    # Make sure it has an `id` field
    if request.json.get('id') is None:
        return render_json(406, {'error': 'Invalid Stripe event'})

    try:
        
        # Retrieve legit event from Stripe 
        safe_event = PaymentEvent.retrieve(
            event_id=request.json.get('id')
        )
        
        # Get data
        data = safe_event['data']['object']
        
        # Get IDs
        customer_id = data['customer']
        subscription_id = data['id']
        
        # Get subscription 
        subscription = Subscription.get_plan_by_subscription_id(subscription_id)
        
        # Check if the start/end dates for this billing cycle are different 
        payload_start = localize_datetime(utc_timestamp_to_datetime(data['current_period_start']))
        start_diff = subscription.current_period_start != payload_start
        current_app.logger.debug('Comparing `current_period_start` datetimes:\n\t{:<35}{}\n\t{:<35}{}\n\t{:<35}{}'.format(
            'start_diff:', start_diff,
            'payload_start:', format_datetime(payload_start),
            'subscription.current_period_start:', format_datetime(subscription.current_period_start)
        ))
        
        payload_end = localize_datetime(utc_timestamp_to_datetime(data['current_period_end']))
        end_diff = subscription.current_period_end != payload_end
        current_app.logger.debug('Comparing `current_period_end` datetimes:\n\t{:<35}{}\n\t{:<35}{}\n\t{:<35}{}'.format(
            'end_diff:', end_diff,
            'payload_end:', format_datetime(payload_end),
            'subscription.current_period_end:', format_datetime(subscription.current_period_end)
        ))
        
        if start_diff or end_diff:
            renewal = True
        else:
            renewal = False

        # If this subscription is being renewed, reset values 
        if renewal:

            # Reset values
            subscription.plan_id = subscription.new_plan_id
            current_app.logger.debug('[DB] Reset plan ID')
            
            # Start date
            old_start = subscription.current_period_start
            
            subscription.current_period_start = payload_start
            
            current_app.logger.debug('[DB] Reset next billing start:\n\tOld: {}\n\tNew: {}'.format(
                format_datetime(old_start),
                format_datetime(subscription.current_period_start)
            ))
            
            # End date
            old_end = subscription.current_period_end
            
            subscription.current_period_end = payload_end
            
            current_app.logger.debug('[DB] Reset next billing end:\n\tOld: {}\n\tNew: {}'.format(
                format_datetime(old_end), 
                format_datetime(subscription.current_period_end)
            ))
            
            if subscription.subscription_schedule_id:
            
                # Release schedule (Production: 1 try)
                if not current_app.config['DEBUG']:
                    subscription_schedule = PaymentSubscriptionSchedule.release(
                        subscription_schedule_id=subscription.subscription_schedule_id
                    )
                
                # Release schedule (Debug: Try until success, since Test Clock can ignore this when making modifications)
                else:
                    subscription_schedule = None
                    while subscription_schedule is None:
                        try:
                            subscription_schedule = PaymentSubscriptionSchedule.release(
                                subscription_schedule_id=subscription.subscription_schedule_id
                            )
                        except:
                            pass
                
                subscription.subscription_schedule_id = None
                current_app.logger.debug('[Stripe] Released subscription schedule {}'.format(subscription_schedule.id))
            
            else:
                current_app.logger.debug('No subscription schedule to release') 
            
            # Save 
            subscription.save()
        
        else:
            current_app.logger.debug('This was a change to the same billing cycle - keeping saved dates:\n\t{:<7}{}\n\t{:<7}{}'.format(
                'Start:',
                format_datetime(subscription.current_period_start),
                'End:',
                format_datetime(subscription.current_period_end)
            ))
    
    # We could not parse the event
    except InvalidRequestError as e:
        
        return render_json(422, {'error': str(e)})
    
    # Return a 200 because something is really wrong and we want Stripe to stop trying to fulfill this webhook request
    except Exception as e:
        return render_json(200, {'error': str(e)})

    # Success
    return render_json(200, {'success': True})
