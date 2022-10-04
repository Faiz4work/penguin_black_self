import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.video.models import Video, Tournament, Team, Country, videos_teams
from badmintontv.blueprints.admin.forms import SearchForm, BulkDeleteForm, VideoForm
from badmintontv.blueprints.admin.views.dashboard import admin


@admin.route('/video', defaults={'page': 1})   # Set default page to 1
@admin.route('/video/page/<int:page>')
def videos(page):
    '''Displays all videos with various information'''
    
    # Set-up forms 
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    order_values = utils.sort_order(
        model=Video
    )

    paginated_videos, count = utils.simple_paginate(
        model=Video,
        order_values=order_values,
        page=page
    )

    # Render index template 
    return render_template(
        'admin/video/index.html',
        form=search_form, 
        bulk_form=bulk_form,
        videos=paginated_videos,
        count=count
    )


@admin.route('/video/edit/<int:id>', methods=['GET', 'POST'])
def videos_edit(id):
    '''Edit a video's details'''
    
    # Get user by ID 
    video = Video.query.get(id)
    
    # Populate form with video data
    form = VideoForm(obj=video)
    
    # POST request 
    if form.validate_on_submit():
        
        old_tournament = video.tournament

        # Populate video with form 
        form.populate_obj(video)
        
        # Edit tournament start-end dates
        new_tournament = video.tournament
        _edit_tournament_dates(
            tournaments=[old_tournament, new_tournament]
        )

        # Save to DB
        video.save()

        # Flash confirmation message
        flash('Video has been updated successfully.', 'success')
        
        # Re-direct to users page 
        return redirect(url_for('admin.videos_edit', id=id))

    # Get all countries for this video
    all_countries = Country.query.join(Team).join(videos_teams).join(Video).filter(
        Video.name == video.name
    ).all()

    # Form submission failed - keep form data 
    return render_template('admin/video/edit.html', 
        form=form, 
        video=video,
        all_countries=all_countries
    )


def _edit_tournament_dates(tournaments):
    '''Edits `start_date` and `end_date` in `tournaments` to make sure they're correct'''
    
    for tournament in tournaments:
        
        start_date = None
        end_date = None
        for video_temp in tournament.videos:
            date = video_temp.date
            
            # Initial assignment 
            if not start_date and not end_date:
                start_date = date 
                end_date = date
    
            else:
                
                # Start date comparison
                if date < start_date:
                    start_date = date
                    
                # End date comparison
                if date > end_date:
                    end_date = date
        
        tournament.start_date = start_date
        tournament.end_date = end_date
            
        # Save to DB
        tournament.save()


@admin.route('/video/bulk_delete', methods=['POST'])
def videos_bulk_delete():
    '''Bulk delete videos'''
    
    # Set-up form 
    form = BulkDeleteForm()

    # POST request 
    if form.validate_on_submit():
        
        # Get list of IDs to delete 
        ids = Video.get_bulk_action_ids(
            scope=request.form.get('scope'),        # Either 'all_selected_items' or 'all_search_results'
            ids=request.form.getlist('bulk_ids'),   # All selected checkboxes
            query=request.form.get('q', '')         # Search term
        )

        from badmintontv.blueprints.admin.tasks import delete_rows

        # Delete all selected users 
        delete_count = delete_rows.delay(Video, ids)

        # Flash success message 
        flash('{} video(s) were scheduled to be deleted.'.format(len(ids)), 'success')
    
    # Flash error message
    else:
        flash('No videos were deleted, something went wrong.', 'error')

    # Re-direct to users page 
    return redirect(url_for('admin.videos'))
