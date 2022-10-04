import click
import random

from datetime import datetime, timedelta
from faker import Faker
from tqdm import tqdm

from libs.util_ip import ip_to_region
from badmintontv.app import create_app
from badmintontv.extensions import db
from badmintontv.blueprints.user.models import User
from badmintontv.blueprints.billing.models.subscription import Subscription
from badmintontv.blueprints.billing.models.invoice import Invoice
from badmintontv.blueprints.view.models import View
from badmintontv.blueprints.video.models import Video

# Create an app context for the database connection 
app = create_app()
db.app = app

# Used to generate fake data 
fake = Faker()


def _log_status(count, model_label):
    '''
    Log the output of how many records were created

    Params:
        count (int):         Number of records created
        model_label (str):   Name of the model
    '''
    click.echo('Created {} {}'.format(count, model_label))


def _bulk_insert(model, data, label):
    '''
    Bulk insert data to a specific model and log it
    
    Note: This is much more efficient than adding 1 row at a time in a loop
    
    Params:
        model (SQLAlchemy model):   Model being affected 
        data (list):                Data to be saved
        label (str):                Label for the print output
    '''
    with app.app_context():
        
        # Delete all users 
        model.query.delete()
        db.session.commit()
        
        # Insert all users 
        db.engine.execute(model.__table__.insert(), data)

        # Print/Echo
        _log_status(model.query.count(), label)


@click.group()
def cli():
    '''Add items to the database'''
    pass


@click.command()
def users(num_users=70):
    '''
    Generate fake users
    
    Params:
        num_users (int): Number of users to generate 
    '''
    
    random_emails = []
    fake_users = []

    # Print output 
    click.echo('Working...')

    # Populate list of random emails - 1 for each user 
    for i in range(0, num_users-1):
        random_emails.append(fake.email())

    # Make sure seed admin is included 
    random_emails.append(app.config['SEED_ADMIN_EMAIL'])
    
    # Remove duplicates
    random_emails = list(set(random_emails))

    # Loop until we run out of emails 
    progress_bar = tqdm(total=num_users, ncols=60)
    while True:
        if len(random_emails) == 0:
            break

        # Random date-time from 1 year ago to now 
        fake_datetime = fake.date_time_between(
            start_date='-1y', 
            end_date='now'
        ).strftime('%s')

        # Set that as `created_on` 
        created_on = datetime.utcfromtimestamp(
            float(fake_datetime)
        ).strftime('%Y-%m-%dT%H:%M:%S Z')

        # 5% chance of admin, 95% chance of notmal user 
        random_percent = random.random()
        if random_percent >= 0.05:
            role = 'member'
        else:
            role = 'admin'
            
        # 25% chance of each locale 
        random_percent = random.random()
        if 0.25 > random_percent > 0:
            locale = 'en'
        elif 0.50 > random_percent >= 0.25:
            locale = 'ko'
        elif 0.75 > random_percent >= 0.50:
            locale = 'ja'
        elif 1 > random_percent >= 0.75:
            locale = 'zh'

        # Pop and store email 
        email = random_emails.pop()

        # Generate random username
        random_trail = str(int(round((random.random() * 1000))))   # Random numbers at the end 
        username = fake.first_name() + random_trail

        # Random date-time from 1 year ago to now 
        fake_datetime = fake.date_time_between(
            start_date='-1y', 
            end_date='now'
        ).strftime('%s')

        # Set that as `current_sign_in_on` 
        current_sign_in_on = datetime.utcfromtimestamp(
            float(fake_datetime)
        ).strftime('%Y-%m-%dT%H:%M:%S Z')

        # Random IP address
        current_sign_in_ip = fake.ipv4()
        last_sign_in_ip = fake.ipv4()

        params = {
            'created_on': created_on,
            'updated_on': created_on,
            'role': role,
            'username': username,
            'email': email,
            'password': User.encrypt_password('password'),    # Encrypt 'password' as password 
            'sign_in_count': random.random() * 100,           # Random sign-in count 
            'current_sign_in_on': current_sign_in_on,
            'current_sign_in_ip': current_sign_in_ip,
            'current_sign_in_region': ip_to_region(current_sign_in_ip),
            'last_sign_in_on': current_sign_in_on,
            'last_sign_in_ip': last_sign_in_ip,
            'locale': locale
        }

        # Ensure the seeded admin is always an admin with the seeded username/password
        if email == app.config['SEED_ADMIN_EMAIL']:
            params['role'] = 'admin'
            params['username'] = app.config['SEED_ADMIN_USERNAME']
            params['password'] = User.encrypt_password(app.config['SEED_ADMIN_PASSWORD'])
            params['confirmed'] = True
            params['locale'] = 'en'

        # Save to list of fake users 
        fake_users.append(params)
        
        # Update progress bar 
        progress_bar.update(1)

    # Close progress bar 
    progress_bar.close()

    # Add everything to DB 
    return _bulk_insert(
        model=User, 
        data=fake_users, 
        label='users'
    )


@click.command()
def subscriptions():
    '''Generate random subscriptions'''
    
    data = []

    # Get all users 
    users = db.session.query(User).all()
    
    # Loop over all users 
    for user in users:

        # 20% chance to generate subscription 
        if random.random() > 0.8:
            
            # 40% chance subsciption is monthly
            if random.random() > 0.6:
                plan = 'monthly'
            else:
                plan = 'yearly'

            params = {
                'user_id': user.id,
                'plan': plan
            }

            # Save it 
            data.append(params)

    # Insert fake invoices into `Invoice` model
    return _bulk_insert(
        model=Subscription, 
        data=data, 
        label='subsciptions'
    )


@click.command()
def invoices():
    '''Generate random invoices'''
    
    data = []

    # Get all users 
    users = db.session.query(User).all()

    # Loop over all users 
    for user in users:
        
        # Generate between 1-12 invoices 
        num_invoices_to_generate = random.randint(1, 12)
        for i in range(0, num_invoices_to_generate):
            
            # Create a fake unix timestamps 
            created_on = fake.date_time_between(
                start_date='-1y', end_date='now'
            ).strftime('%s')
            
            period_start_on = fake.date_time_between(
                start_date='now', end_date='+1y'
            ).strftime('%s')
            
            period_end_on = fake.date_time_between(
                start_date=period_start_on, end_date='+14d'
            ).strftime('%s')
            
            exp_date = fake.date_time_between(
                start_date='now', end_date='+2y'
            ).strftime('%s')

            # Format
            created_on = datetime.utcfromtimestamp(
                float(created_on)
            ).strftime('%Y-%m-%dT%H:%M:%S Z')
            
            period_start_on = datetime.utcfromtimestamp(
                float(period_start_on)
            ).strftime('%Y-%m-%d')
            
            period_end_on = datetime.utcfromtimestamp(
                float(period_end_on)
            ).strftime('%Y-%m-%d')
            
            exp_date = datetime.utcfromtimestamp(
                float(exp_date)
            ).strftime('%Y-%m-%d')

            # Lists of available plans and cards
            plans = ['BadmintonTV Monthly', 'BadmintonTV Yearly']
            cards = ['Visa', 'Mastercard', 'AMEX', 'J.C.B', "Diner's Club"]

            # Create invoice parameters
            params = {
                'created_on': created_on,
                'updated_on': created_on,
                'user_id': user.id,
                'receipt_number': fake.md5(),
                'description': str(random.choice(plans)),
                'period_start_on': period_start_on,
                'period_end_on': period_end_on,
                'currency': 'usd',
                'tax': random.random() * 100,
                'tax_percent': random.random() * 10,
                'total': random.random() * 1000,
                'brand': random.choice(cards),
                'last4': random.randint(1000, 9000),
                'exp_date': exp_date
            }

            # Save it 
            data.append(params)

    # Insert fake invoices into `Invoice` model
    return _bulk_insert(
        model=Invoice, 
        data=data, 
        label='invoices'
    )
    


@click.command()
def views():
    '''Generate random views'''
    
    data = []

    users = db.session.query(User).all()
    
    num_videos = db.session.query(Video).count()    

    # Loop over all users 
    for user in users:
        
        # Generate views 
        num_views = 100
        for i in range(0, num_views):
            
            random_id = random.randrange(0, num_videos) 
            video = db.session.query(Video)[random_id]
            
            duration = video.highlights_duration
            
            duration_seconds = timedelta(
                hours=duration.hour, 
                minutes=duration.minute, 
                seconds=duration.second
            )
            duration_seconds = duration_seconds.total_seconds()
            duration_seconds = int(duration_seconds)
            print(duration, duration_seconds)
            
            # Create a fake unix timestamps 
            created_on = fake.date_time_between(
                start_date='-1y', end_date='now'
            ).strftime('%s')

            # Format
            created_on = datetime.utcfromtimestamp(
                float(created_on)
            ).strftime('%Y-%m-%dT%H:%M:%S Z')
            
            # Fake IP 
            ip = fake.ipv4()

            # Object parameters
            params = {
                'created_on': created_on,
                'updated_on': created_on,
                'ip': ip,
                'country': ip_to_region(ip),
                'duration': duration,
                'user_id': user.id,
                'video_id': video.id,
            }

            # Save it 
            data.append(params)

    # Insert fake invoices into `Invoice` model
    return _bulk_insert(
        model=View, 
        data=data, 
        label='views'
    )
    

@click.command()
@click.pass_context
def all(ctx):
    '''Generate all data'''
    ctx.invoke(users)
    ctx.invoke(subscriptions)
    ctx.invoke(invoices)
    ctx.invoke(views)


cli.add_command(users)
cli.add_command(subscriptions)
cli.add_command(invoices)
cli.add_command(views)
cli.add_command(all)
