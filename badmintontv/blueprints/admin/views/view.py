import os
import json

from flask import request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.view.models import View
from badmintontv.blueprints.video.models import Video
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.admin.views.dashboard import admin
from badmintontv.blueprints.admin.forms import SearchForm


@admin.route('/view', defaults={'page': 1})   # Set default page to 1
@admin.route('/view/page/<int:page>')
def views(page):
    '''Displays all views with various information'''

    # Set-up forms 
    search_form = SearchForm()

    order_values = utils.sort_order(
        model=View,
        prepend='views.'
    )

    # Get users on this page
    paginated_views, count = utils.paginate_joins(
        model=View,
        models_join_on=[Video, User],
        order_values=order_values,
        page=page
    )

    # Render index template 
    return render_template(
        'admin/view/index.html',
        form=search_form, 
        views=paginated_views,
        count=count
    )
