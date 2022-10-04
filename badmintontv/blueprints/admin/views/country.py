import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Country, Team, Video, videos_teams
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, CountryForm
from badmintontv.blueprints.admin.views.dashboard import admin


@admin.route('/country', defaults={'page': 1})   # Set default page to 1
@admin.route('/country/page/<int:page>')
def countries(page):
    '''Displays all countries with various information'''
    
    # Set-up forms 
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    order_values = utils.sort_order(
        model=Country
    )

    # Get users on this page
    paginated_countries, count = utils.simple_paginate(
        model=Country,
        order_values=order_values,
        page=page
    )

    # Render index template 
    return render_template(
        'admin/country/index.html',
        form=search_form, 
        bulk_form=bulk_form,
        countries=paginated_countries,
        count=count
    )


@admin.route('/country/edit/<int:id>', methods=['GET', 'POST'])
def countries_edit(id):
    '''Edit a country's details'''
    
    # Get user by ID 
    country = Country.query.get(id)
    
    # Populate form with countries data
    form = CountryForm(obj=country)
    
    # POST request 
    if form.validate_on_submit():

        # Populate country with form 
        form.populate_obj(country)

        # Save to DB
        country.save()

        # Flash confirmation message
        flash('Country has been updated successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.countries_edit', id=id))
    
    # Get all videos for this country
    all_videos = Video.query.join(videos_teams).join(Team).join(Country).filter(
        Country.name == country.name
    ).all()

    # Form submission failed - keep form data 
    return render_template('admin/country/edit.html', 
        form=form, 
        country=country,
        all_videos=all_videos
    )


@admin.route('/country/bulk_delete', methods=['POST'])
def countries_bulk_delete():
    '''Bulk delete countries'''
    
    # Set-up form 
    form = BulkDeleteForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get list of IDs to delete 
        ids = Country.get_bulk_action_ids(
            scope=request.form.get('scope'),        # Either 'all_selected_items' or 'all_search_results'
            ids=request.form.getlist('bulk_ids'),   # All selected checkboxes
            query=request.form.get('q', '')         # Search term
        )
        
        from badmintontv.blueprints.admin.tasks import delete_rows

        # Delete all selected users 
        delete_count = delete_rows.delay(Country, ids)

        # Flash success message 
        flash('{} country(s) were scheduled to be deleted.'.format(len(ids)), 'success')
    
    # Flash error message
    else:
        flash('No countries were deleted, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.countries'))
