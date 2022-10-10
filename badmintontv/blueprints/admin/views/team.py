import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Country, Team
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, TeamForm
from badmintontv.blueprints.admin.views.dashboard import admin
from badmintontv.extensions import db, csrf


@admin.route('/team', defaults={'page': 1})   # Set default page to 1
@admin.route('/team/page/<int:page>')
def teams(page):
    '''Displays all teams with various information'''
    
    # Set-up forms 
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    order_values = utils.sort_order(
        model=Team
    )

    # Get users on this page
    paginated_teams, count = utils.simple_paginate(
        model=Team,
        order_values=order_values,
        page=page,
        num_items=10,
    )      

    # Render index template 
    return render_template(
        'admin/team/index.html',
        form=search_form, 
        bulk_form=bulk_form,
        teams=paginated_teams,
        count=count
    )


@admin.route('/team/edit/<int:id>', methods=['GET', 'POST'])
def teams_edit(id):
    '''Edit a team's details'''
    
    # Get user by ID 
    team = Team.query.get(id)
    
    # Populate form with teams data
    form = TeamForm(obj=team)
    
    # POST request 
    if form.validate_on_submit():

        # Populate teams with form 
        form.populate_obj(team)

        # Save to DB
        team.save()

        # Flash confirmation message
        flash('Team has been updated successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.teams_edit', id=id))

    # Form submission failed - keep form data 
    return render_template('admin/team/edit.html', 
        form=form, 
        team=team
    )


@admin.route('/team/bulk_delete', methods=['POST'])
def teams_bulk_delete():
    '''Bulk delete teams'''
    
    # Set-up form 
    form = BulkDeleteForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get list of IDs to delete 
        ids = Team.get_bulk_action_ids(
            scope=request.form.get('scope'),        # Either 'all_selected_items' or 'all_search_results'
            ids=request.form.getlist('bulk_ids'),   # All selected checkboxes
            query=request.form.get('q', '')         # Search term
        )
        
        from badmintontv.blueprints.admin.tasks import delete_rows
        
        # Delete all selected users 
        delete_count = delete_rows.delay(Team, ids)

        # Flash success message 
        flash('{} team(s) were scheduled to be deleted.'.format(len(ids)), 'success')
    
    # Flash error message
    else:
        flash('No teams were deleted, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.teams'))


@admin.route("/team/add", methods=["GET", "POST"])
@csrf.exempt
def add_team():
    if request.method == "POST":
        team_name = request.form.get("team_name")
        country = request.form.get("country")
        if country != "None":
            country = Country.query.get(int(country))
        else:
            country = None
        
        t = Team(
            name = team_name,
            country = country,
        )
        db.session.add(t)
        db.session.commit()
        
        return redirect(url_for("admin.teams"))
            
    
    countries = Country.query.all()
    return render_template("admin/team/add_team.html",
                           countries=countries)
