import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Tournament
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, TournamentForm
from badmintontv.blueprints.admin.views.dashboard import admin
from badmintontv.extensions import db, csrf


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
@csrf.exempt
def tournaments_edit(id):
    '''Edit a tournament's details'''
    
    # Get user by ID 
    tournament = Tournament.query.get(id)
    
    # Populate form with tournaments data
    # form = TournamentForm(obj=tournament)
    
    # POST request 
    if request.method == "POST":
        t_name = request.form.get("tournament_name")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        
        tournament.name = t_name
        tournament.start_date = start_date
        tournament.end_date = end_date
        
        db.session.commit()

        # Flash confirmation message
        flash('Tournament has been updated successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.tournaments'))

    # Form submission failed - keep form data 
    return render_template('admin/tournament/edit.html', 
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


@admin.route("/tournament/add", methods=["GET", "POST"])
@csrf.exempt
def add_tournament():
    if request.method == "POST":
        t_name = request.form.get("tournament_name")
        s_date = request.form.get("start_date")
        e_date = request.form.get("end_date")
        
        t = Tournament(
            name = t_name,
            start_date = s_date,
            end_date = e_date,
        )
        db.session.add(t)
        db.session.commit()
        return redirect(url_for('admin.tournaments'))
        
    
    return render_template("admin/tournament/add_tournament.html")


@admin.route("/tournament/delete/<int:id>")
def delete_tournament(id):
    t = Tournament.query.get(id)
    db.session.delete(t)
    db.session.commit()
    flash("Tournament has been deleted.", "success")
    return redirect(url_for('admin.tournaments'))

