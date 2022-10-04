from flask import redirect, request, flash, url_for, render_template
from flask_login import current_user
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from config import settings
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, UserForm, UserCancelSubscriptionForm
from badmintontv.blueprints.admin.views.dashboard import admin


@admin.route('/users', defaults={'page': 1})   # Set default page to 1
@admin.route('/users/page/<int:page>')
def users(page):
    '''Displays all users with various information'''
    
    # Set-up forms 
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    order_values = utils.sort_order(
        model=User
    )

    # Get users on this page
    paginated_users, count = utils.paginate(
        model=User,
        on_top=User.role.asc(),
        order_values=order_values,
        page=page
    )  

    # Render index template 
    return render_template(
        'admin/user/index.html',
        form=search_form, 
        bulk_form=bulk_form,
        users=paginated_users,
        LANGUAGES=settings.LANGUAGES,
        count=count
    )


@admin.route('/users/edit/<int:id>', methods=['GET', 'POST'])
def users_edit(id):
    '''
    Edit a user account's:
    - Username
    - Role
    - Active/Disabled status
    '''
    
    # Get user by ID 
    user = User.query.get(id)
    
    # Populate form with user data
    form = UserForm(obj=user)

    # Get recent billing history 
    invoices = Invoice.billing_history(current_user)
    
    # If user is subscribed
    if current_user.subscription:
        
        # Get next invoice 
        upcoming = Invoice.upcoming(current_user.payment_id)
    
    # Use is not subscribed - no upcoming invoice
    else:
        upcoming = None
    
    # POST request 
    if form.validate_on_submit():
        
        # Make sure the last admin can't:
        # - Demote itself to a normal member
        # - Deactivate itself 
        is_last_admin = User.is_last_admin(
            user,
            new_role=request.form.get('role'),
            new_active=request.form.get('active')
        )
        if is_last_admin:
            
            # Flash error message
            flash('You are the last admin, you cannot do that.', 'error')
            
            # Re-direct to users page 
            return redirect(url_for('admin.users_edit', id=id))

        # Populate user with form 
        form.populate_obj(user)

        # Save to DB
        user.save()

        # Flash confirmation message
        flash('User has been saved successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.users_edit', id=id))

    # Form submission failed - keep form data 
    return render_template('admin/user/edit.html', 
        form=form, 
        user=user,
        invoices=invoices, 
        upcoming=upcoming,
        prices=settings.STRIPE_PRICES,
        LANGUAGES=settings.LANGUAGES
    )


@admin.route('/users/bulk_delete', methods=['POST'])
def users_bulk_delete():
    
    # Set-up form 
    form = BulkDeleteForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get list of IDs to delete 
        ids = User.get_bulk_action_ids(
            scope=request.form.get('scope'),        # Either 'all_selected_items' or 'all_search_results'
            ids=request.form.getlist('bulk_ids'),   # All selected checkboxes
            omit_ids=[current_user.id],             # Omit the current user
            query=request.form.get('q', '')         # Search term
        )
        
        from badmintontv.blueprints.admin.tasks import delete_rows

        # Delete all selected users 
        delete_count = delete_rows.delay(User, ids)

        # Flash success message 
        flash('{} user(s) were scheduled to be deleted.'.format(len(ids)), 'success')
    
    # Flash error message
    else:
        flash('No users were deleted, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.users'))


@admin.route('/users/cancel_subscription', methods=['POST'])
def users_cancel_subscription():
    '''Cancel a user's subscription'''
    
    # Set-up empty form 
    form = UserCancelSubscriptionForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get user by ID
        user = User.query.get(
            request.form.get('id')
        )

        # If the user exists
        if user:
            
            # Cancel subscription
            subscription = Subscription()
            if subscription.cancel(user):
                
                # Flash confirmation message
                flash('Subscription has been cancelled for {}.'.format(user.name), 'success')
        
        # Flash error message
        else:
            flash('No subscription was cancelled, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.users'))
