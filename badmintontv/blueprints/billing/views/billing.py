from flask import Blueprint, current_app, render_template, url_for, request, redirect, flash
from flask_login import login_required, current_user
from flask_babel import gettext as _

from config import settings
from libs.util_json import render_json
from badmintontv.blueprints.billing.forms import CreditCardForm, UpdateSubscriptionForm, CancelSubscriptionForm
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.billing.decorators import subscription_required, handle_stripe_exceptions

billing = Blueprint(
    'billing', 
    __name__, 
    template_folder='../templates', 
    url_prefix='/subscription'
)


@billing.route('/pricing')
def pricing():
    '''Displays pricing'''
    
    # User already has a subscription - redirect to update subscription URL
    if current_user.is_authenticated and current_user.subscription:
        return redirect(url_for('billing.update'))

    # ...
    form = UpdateSubscriptionForm()

    # Render pricing page
    return render_template(
        'pricing.html',
        form=form,
        prices=settings.STRIPE_PRICES
    )


@billing.route('/create', methods=['GET', 'POST'])
@handle_stripe_exceptions    # Handles Stripe's exceptions to display more user-friendly error 
@login_required
def create():
    '''Creates a new subscription'''
    
    # If user is already subscribed, re-direct to the settings page
    if current_user.subscription:
        flash('You already have an active subscription.', 'info')
        return redirect(url_for('user.settings'))

    # Get plan ID from URL
    id = request.args.get('id')
    
    # Get dict with information about the plan 
    plan = Subscription.get_plan_by_id(
        id=id
    )

    # `subscription_plan`: Guards against an invalid or missing plan
    # `GET`: This makes sure the user is viewing the subscription page, and not submitting the actual form (POST request)
    # This protects our app from users manually changing the URL parameters
    if plan is None and request.method == 'GET':
        flash('Sorry, that plan does not exist.', 'error')
        
        # Re-direct to the pricing page
        return redirect(url_for('billing.pricing'))

    # Get Stripe publishable key 
    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    
    # Set-up payment form
    form = CreditCardForm(
        stripe_key=stripe_key,
        id=id
    )

    # POST request
    if form.validate_on_submit():
        
        id = request.form.get('id')
        
        # Create a new subscription 
        subscription = Subscription()
        created = subscription.create(
            user=current_user,
            name=request.form.get('name'),
            id=id,
            token=request.form.get('stripe_token')     # One-time use token from Stripe
        )

        # If subscription was create, flash confirmation message
        if created:
            
            # Get plan name 
            plan_name = settings.STRIPE_PRICES[id]['name'].lower()
            
            flash(
                _(
                    'Awesome, thanks for subscribing to the %(plan)s plan!', 
                    plan=plan_name
                ), 
                'success'
            )
        
        # Otherwise, flash error message
        else:
            
            # Failure is likely due to not enabling JS in the browser, since the Stripe token would be empty
            flash('You must enable JavaScript for this request.', 'warning')

        # Re-direct user to settings page
        return redirect(url_for('user.settings'))

    # Render this page (and DON'T erase what's in the form)
    return render_template(
        'payment_method.html',
        form=form, 
        plan=plan
    )


@billing.route('/update', methods=['GET', 'POST'])
@handle_stripe_exceptions
@subscription_required      # Subscription is required 
@login_required
def update():
    '''Update/Change a subscription'''
    
    # Get user's new plan ID
    next_plan_id = current_user.subscription.new_plan_id
    
    # Get new plan
    next_plan = Subscription.get_plan_by_id(
        id=next_plan_id
    )
    
    # Get new plan ID
    new_plan_id = Subscription.get_new_plan(
        keys=request.form.keys()    # List of all form field names (eg. 'submit_monthly' if we change to the monthly plan)
    )

    # Get new plan info 
    new_plan = Subscription.get_plan_by_id(
        id=new_plan_id
    )

    # Guard against an invalid/missing (`new_plan_doesnt_exist`), or identical plan (`is_same_plan`)
    new_plan_doesnt_exist = new_plan_id is not None and new_plan is None
    is_same_plan = new_plan_id == next_plan['id']
    if (new_plan_doesnt_exist or is_same_plan) and request.method == 'POST':
        
        # Re-direct to change subscription page
        return redirect(url_for('billing.update'))

    # ...
    form = UpdateSubscriptionForm()

    # POST request is valid 
    if form.validate_on_submit():
        
        # Update subscription 
        subscription = Subscription()
        updated = subscription.update(
            user=current_user,
            plan_id=new_plan.get('id')
        )

        # If success, flash confirmation message
        if updated:
            flash('Your subscription has been updated.', 'success')
            
            # Re-direct to settings page
            return redirect(url_for('user.settings'))

    # Render this page (and DON'T erase what's in the form)
    return render_template(
        'pricing.html',
        form=form,
        prices=settings.STRIPE_PRICES,
        next_plan=next_plan
    )


@billing.route('/cancel', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def cancel():
    '''Cancel a subscription'''
    
    # If user is not subscribed, re-direct to settings page 
    if not current_user.subscription:
        flash('You do not have an active subscription.', 'error')
        return redirect(url_for('user.settings'))

    # Set-up an empty form 
    form = CancelSubscriptionForm()

    # POST request - always valid
    if form.validate_on_submit():
        
        # Cancel subscription for this user 
        subscription = Subscription()
        cancelled = subscription.cancel(
            user=current_user
        )

        # If success, flash confirmation message
        if cancelled:
            flash('Sorry to see you go, your subscription has been cancelled.', 'success')
            
            # Re-direct to settings page 
            return redirect(url_for('user.settings'))

    # Render this page (and DON'T erase what's in the form)
    return render_template('cancel.html', form=form)


@billing.route('/update_payment_method', methods=['GET', 'POST'])
@handle_stripe_exceptions     # If there's an issue with Stripe, this handler will provide the real error message
@login_required
def update_payment_method():
    '''Used to update a user's payment method'''
    
    # Safety check; If the user doesn't have a credit card, we can't update it 
    if not current_user.card:
        flash('You do not have a payment method on file.', 'error')
        
        # Re-direct to settings page 
        return redirect(url_for('user.settings'))

    active_plan_id = current_user.subscription.plan_id

    # Get current active subscription 
    active_plan = Subscription.get_plan_by_id(
        id=active_plan_id
    )

    # Get credit card info 
    card = current_user.card
    
    # Get Stripe API key 
    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    
    # Set-up credit card form 
    form = CreditCardForm(
        stripe_key=stripe_key,
        id=active_plan_id,
        name=current_user.name
    )

    # POST request
    if form.validate_on_submit():
        
        # Update subscription
        subscription = Subscription()
        updated = subscription.update_payment_method(
            user=current_user,
            card=card,
            name=request.form.get('name'),
            token=request.form.get('stripe_token')
        )
        
        # Updated worked - flash success message
        if updated:
            flash('Your payment method has been updated.', 'success')
        
        # Otherwise, flash error message
        else:
            
            # Failure is likely due to not enabling JS in the browser, since the Stripe token would be empty
            flash('You must enable JavaScript for this request.', 'warning')

        # Re-direct to settings page 
        return redirect(url_for('user.settings'))

    # Render this page (and DON'T erase what's in the form)
    return render_template(
        'payment_method.html', 
        form=form,
        plan=active_plan, 
        card_last4=str(card.last4)   # Pass last 4 digits of credit card 
    )


@billing.route('/billing_details', defaults={'page': 1})
@billing.route('/billing_details/page/<int:page>')
@handle_stripe_exceptions
@login_required
def billing_details(page):
    '''Shows billing details'''
    
    # Get most recent invoices 
    #invoices = Invoice.billing_history(current_user)
    
    # Get paginated invoices for this user
    paginated_invoices = Invoice.query.filter( 
        Invoice.user_id == current_user.id 
    ).order_by( 
        Invoice.created_on.desc() 
    ).paginate(page, 12, True)

    # If user is subscribed
    if current_user.subscription:
        
        # Get upcoming invoice
        upcoming = Invoice.upcoming(
            customer_id=current_user.payment_id
        )
    
    # User not subscribed - no upcoming invoices
    else:
        upcoming = None

    # Render page
    return render_template(
        'billing_details.html',
        paginated_invoices=paginated_invoices, 
        upcoming=upcoming
    )
