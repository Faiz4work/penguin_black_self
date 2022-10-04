from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import current_user

page = Blueprint(
    'page', 
    __name__, 
    template_folder='templates'
)

@page.route('/test')
def test():
    return render_template('test.html')

@page.route('/')
def index():
    
    # Logged out --> Home page 
    if not current_user.is_authenticated:
        return render_template('home.html')
    
    # Subscribed/Admin --> Latest Tournament page 
    elif current_user.subscription or current_user.role == 'admin':
        return redirect(url_for('video.latest_tournament'))
    
    # Otherwise --> Pricing page 
    return redirect(url_for('billing.pricing'))



@page.route('/language/<language>')
def set_language(language=None):
    '''Set language for this session'''
    
    session['language'] = language
    
    return redirect(url_for('page.index'))


@page.route('/announcements')
def announcements():
    return render_template('announcements.html')


@page.route('/faq')
def faq():
    return render_template('faq.html')
