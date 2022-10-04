from flask import render_template, request
from sqlalchemy import text

import libs.util_sqlalchemy as utils

from badmintontv.blueprints.admin.forms import SearchForm
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.admin.views.dashboard import admin


@admin.route('/invoices', defaults={'page': 1})
@admin.route('/invoices/page/<int:page>')
def invoices(page):
    
    # Set-up search form 
    search_form = SearchForm()

    order_values = utils.sort_order(
        model=Invoice,
        prepend='invoices.'
    )

    paginated_invoices, count = utils.paginate_join(
        model=Invoice,
        model_join_on=User,
        order_values=order_values,
        page=page
    )      

    # Render invoices page 
    return render_template(
        'admin/invoice/index.html',
        form=search_form, 
        invoices=paginated_invoices,
        count=count
    )
