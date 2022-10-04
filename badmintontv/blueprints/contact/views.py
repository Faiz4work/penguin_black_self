from flask import Blueprint, flash, redirect, request, url_for, render_template
from flask_login import current_user

from badmintontv.blueprints.contact.forms import ContactForm

contact = Blueprint(
    'contact', 
    __name__, 
    template_folder='templates'
)


@contact.route('/contact', methods=['GET', 'POST'])
def index():
    '''Single page for contact form'''
    
    form = ContactForm(
        obj=current_user    # Pre-populate the email field if the user is signed in
    )

    # POST request 
    if request.method == "POST":
        if form.validate_on_submit():
            
            # This prevents circular imports
            from badmintontv.blueprints.contact.tasks import deliver_contact_email

            # Send email in background (Celery feature)
            deliver_contact_email.delay(
                request.form.get('email'),
                request.form.get('subject'),
                request.form.get('text')
            )

            flash('Your message has been send, please expect a response within 48 working hours.', 'success')
            
            # Redirect to empty endpoint (as opposed to rendering it)
            return redirect(url_for('contact.index'))

    # Render template
    # Send the form so that fields aren't lost if there are missing fields 
    return render_template('index.html', form=form)
