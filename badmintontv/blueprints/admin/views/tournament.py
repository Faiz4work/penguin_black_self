import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Tournament
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, TournamentForm
from badmintontv.blueprints.admin.views.dashboard import admin


@admin.route('/tournament', defaults={'page': 1})   # Set default page to 1
@admin.route('/tournament/page/<int:page>')
def tournaments(page):
    '''Displays all tournaments with various information'''
    
    # Set-up forms 
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    order_values = utils.sort_order(
        model=Tournament
    )

    paginated_tournaments, count = utils.simple_paginate(
        model=Tournament,
        order_values=order_values,
        page=page
    )  

    # Render index template 
    return render_template(
        'admin/tournament/index.html',
        form=search_form, 
        bulk_form=bulk_form,
        tournaments=paginated_tournaments,
        count=count
    )


@admin.route('/tournament/edit/<int:id>', methods=['GET', 'POST'])
def tournaments_edit(id):
    '''Edit a tournament's details'''
    
    # Get user by ID 
    tournament = Tournament.query.get(id)
    
    # Populate form with tournaments data
    form = TournamentForm(obj=tournament)
    
    # POST request 
    if form.validate_on_submit():

        # Populate tournaments with form 
        form.populate_obj(tournament)

        # Save to DB
        tournament.save()

        # Flash confirmation message
        flash('Tournament has been updated successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.tournaments_edit', id=id))

    # Form submission failed - keep form data 
    return render_template('admin/tournament/edit.html', 
        form=form, 
        tournament=tournament
    )


@admin.route('/tournament/bulk_delete', methods=['POST'])
def tournaments_bulk_delete():
    '''Bulk delete tournaments'''
    
    # Set-up form 
    form = BulkDeleteForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get list of IDs to delete 
        ids = Tournament.get_bulk_action_ids(
            scope=request.form.get('scope'),        # Either 'all_selected_items' or 'all_search_results'
            ids=request.form.getlist('bulk_ids'),   # All selected checkboxes
            query=request.form.get('q', '')         # Search term
        )

        from badmintontv.blueprints.admin.tasks import delete_rows

        # Delete all selected users 
        delete_count = delete_rows.delay(Tournament, ids)

        # Flash success message 
        flash('{} tournament(s) were scheduled to be deleted.'.format(len(ids)), 'success')
    
    # Flash error message
    else:
        flash('No tournaments were deleted, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.tournaments'))
