from flask import Blueprint, redirect, request, flash, url_for, render_template, current_app
from flask_login import login_required, login_user, current_user, logout_user

from libs.safe_next_url import safe_next_url
from badmintontv.blueprints.user.decorators import anonymous_required
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.user.forms import BeginSignupForm, SignupForm, LoginForm, BeginPasswordResetForm, PasswordResetForm, UpdateCredentials, UpdateLocaleForm
from badmintontv.blueprints.contact.views import contact
from badmintontv.extensions import csrf

user = Blueprint(
    'user', 
    __name__, 
    template_folder='templates'
)


@user.route('/begin_signup', methods=['GET', 'POST'])
@anonymous_required()
@csrf.exempt
def begin_signup():
    '''Initial phase of user sign up (sends confirmation email)'''
    
    form = BeginSignupForm()

    if request.method=="POST":
    # POST request from form 
        if form:
            
            # Start password reset 
            user = User.initialize_signup(
                username=request.form.get('username'),
                email=request.form.get('email'),
                password=request.form.get('password')
            )

            # Flash confirmation message 
            flash('A confirmation email has been sent to {}.'.format(user.email), 'success')

            # Re-direct to log-in page 
            return redirect(url_for('user.login'))

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template('signup.html', form=form)


@user.route('/signup', methods=['GET', 'POST'])
@anonymous_required()
@csrf.exempt
def signup():
    '''Finalize user sign up'''
        
    # Deserialize token 
    user = User.deserialize_token(
        token=request.args.get('signup_token')   # Get serialized token from URL
    )
    
    # If deserialized token didn't result in the user email, token was expired or tampered with
    if user is None:
        
        # Flash error message
        flash('Your signup token has expired or was tampered with.', 'error')
        
        # Re-direct to password reset page (initial stage)
        return redirect(url_for('user.begin_signup'))

    # Set user to `confirmed`
    user.confirmed = True
    
    # Save user to DB
    user.save()

    # Log user in 
    if login_user(user):
        
        # Flash confirmation message 
        flash('Awesome, thanks for signing up!', 'success')
        
        # Re-direct to settings page 
        return redirect(url_for('user.settings'))
    
    # Serious problem logging in 
    else:
        flash('You could not be signed up. Please contact support.', 'error')
        return redirect(url_for('contact.index'))


@user.route('/settings', methods=['GET'])
@login_required
def settings():
    '''Renders a page with this user's settings'''
    return render_template(
        'settings.html',
        prices=current_app.config.get('STRIPE_PRICES')
    )

    
@user.route('/login', methods=['GET', 'POST'])
@anonymous_required()      # Re-direct a user to another page if they're already logged-in (check function definition for details)
@csrf.exempt
def login():
    '''Logs a user in'''
    
    form = LoginForm(
        next=request.args.get('next')    # Get 'next' variable from URL 
    )

    if request.method == "POST":
        # Form has been submitted 
            
        # Extract form fields 
        identity = request.form.get('identity')
        password = request.form.get('password')
        
        # Get user 
        user = User.find_by_identity(identity)
        print(user)
        # If user was found
        if user:
        
            # And confirmed their email 
            if user.confirmed: 
                
                # And properly authenticated
                if user.authenticated(password=password):
                    
                    # Here, "Remember Me" is enabled by default (`remember=True`)
                    # This is because more often than not users want this enabled
                    # This allows for a less complicated login form
                    #
                    # If however you want them to be able to select whether or not they
                    # should remain logged in then perform the following 3 steps:
                    # 1) Replace 'True' below with: request.form.get('remember', False)
                    # 2) Uncomment the 'remember' field in user/forms.py#LoginForm
                    # 3) Add a checkbox to the login form with the id/name 'remember'
                    if login_user(user, remember=True):
                    
                        # Make sure user is active - we can disable accounts manually that are abusing the system 
                        if user.is_active():
                            
                            # Update tracking information with IP address
                            user.update_activity_tracking(ip_address=request.remote_addr)

                            # Handle optionally redirecting to the next URL safely
                            next_url = request.form.get('next')
                            if next_url:
                                return redirect(safe_next_url(next_url))

                            # Default re-direct to settings page
                            return redirect(url_for('user.settings'))
                        
                        # Account has been disabled - flash message 
                        else:
                            flash('This account has been disabled.', 'error')
                        
                # Can't log-in - flash message
                else:
                    flash('Username/Email or password is incorrect.', 'error')
        
            # Email not confirmed 
            else:
                flash('Your account has not been confirmed.', 'error')
                
        # Email not confirmed 
        else:
            flash('Your account was not found.', 'error')

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template('login.html', form=form)


@user.route('/logout')
@login_required          # If this route is accessed without being logged in, Flask-Login will flash "Please log in to access this page."
def logout():
    '''Logs a user out'''
    
    # Deletes user session 
    logout_user()
    
    # Flash message
    flash('You have been logged out.', 'success')
    
    # Re-direct to log-in page 
    return redirect(url_for('user.login'))


@user.route('/settings/update_credentials', methods=['GET', 'POST'])
@login_required
def update_credentials():
    '''Used to update email and/or password'''
    
    form = UpdateCredentials(
        current_user, 
        uid=current_user.id
    )

    # POST request
    if form.validate_on_submit():
        
        # Get new password from form 
        new_password = request.form.get('password', '')
        
        # Update user's email (no checking required)
        current_user.email = request.form.get('email')

        # If a new password was set, encrypted it 
        if new_password:
            current_user.password = User.encrypt_password(new_password)

        # Save changes to DB
        current_user.save()

        # Flash confirmation message
        flash('Your sign in settings have been updated.', 'success')
        
        # Re-direct to settings page 
        return redirect(url_for('user.settings'))

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template('update_credentials.html', form=form)


@user.route('/account/begin_password_reset', methods=['GET', 'POST'])
@anonymous_required()
def begin_password_reset():
    '''Initial phase of resetting password (sends email)'''
    
    form = BeginPasswordResetForm()

    # POST request 
    if form.validate_on_submit():
        
        # Start password reset 
        user = User.initialize_password_reset(request.form.get('identity'))

        # Flash confirmation message 
        flash('An email has been sent to {}.'.format(user.email), 'success')

        # Re-direct to log-in page 
        return redirect(url_for('user.login'))

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template('begin_password_reset.html', form=form)


@user.route('/account/password_reset', methods=['GET', 'POST'])
@anonymous_required()
def password_reset():
    '''Finalize reset password'''
    
    form = PasswordResetForm(
        reset_token=request.args.get('reset_token')   # Get reset token from URL
    )                                                 # Note: This is supplied after a "?" in the URL, via the following line in `password_reset.txt`:
                                                      # `{{ url_for('user.password_reset', reset_token=reset_token, _external=True) }}`

    # POST request 
    if form.validate_on_submit():
        
        # Deserialize token 
        user = User.deserialize_token(
            token=request.form.get('reset_token')   # Pass in serialized token 
        )

        # If deserialized token didn't result in the user email, token was expired or tampered with
        if user is None:
            
            # Flash error message
            flash('Your reset token has expired or was tampered with.', 'error')
            
            # Re-direct to password reset page (initial stage)
            return redirect(url_for('user.begin_password_reset'))

        # Populate the user with the form 
        form.populate_obj(user)

        # Encrypt new password 
        user.password = User.encrypt_password(request.form.get('password'))
        
        # Save to DB
        user.save()

        # Log user in 
        if login_user(user):
            
            # Flash confirmation message
            flash('Your password has been reset.', 'success')
            
            # Re-direct to settings page 
            return redirect(url_for('user.settings'))

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template('password_reset.html', form=form)


@user.route('/settings/update_locale', methods=['GET', 'POST'])
@login_required
def update_locale():
    '''Updates locale/language'''
    
    # Set-up language preference form 
    form = UpdateLocaleForm(
        locale=current_user.locale
    )

    # POST request 
    if form.validate_on_submit():
        
        # Save locale to user 
        form.populate_obj(current_user)
        current_user.save()
        
        # Flash confirmation message
        flash('Your locale settings have been updated.', 'success')
        
        # Re-direct to settings page 
        return redirect(url_for('user.settings'))

    # If form submission failed, stay on this page (and DON'T erase what's in the form)
    return render_template(
        'update_locale.html', 
        form=form
    )
