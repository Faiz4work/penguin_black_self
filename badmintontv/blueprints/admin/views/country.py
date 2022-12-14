import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Country, Team, Video, videos_teams
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, CountryForm
from badmintontv.blueprints.admin.views.dashboard import admin
from badmintontv.extensions import db, csrf

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
@csrf.exempt
def countries_edit(id):
    '''Edit a country's details'''
    
    # Get user by ID 
    country = Country.query.get(id)
    
    # POST request 
    if request.method == "POST":
        country_name = request.form.get("country_name")
        country.name = country_name
        db.session.commit()
        
        # Flash confirmation message
        flash('Country has been updated successfully.', 'success')
        return redirect(url_for('admin.countries'))
    

    # Form submission failed - keep form data 
    return render_template('admin/country/edit.html',
        country=country,
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


@admin.route("/country/delete/<int:id>")
def delete_country(id):
    c = Country.query.get(id)
    name = c.name
    db.session.delete(c)
    db.session.commit()
    
    flash(f"{name} has been deleted!", "success")
    
    # Re-direct to users page 
    return redirect(url_for('admin.countries'))

@admin.route("/country/add", methods=["GET", "POST"])
@csrf.exempt
def add_country():
    if request.method == "POST":
        country_name = request.form.get("country_name")
        c = Country(
            name = country_name
        )
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('admin.countries'))
        
    return render_template("admin/country/add_country.html")