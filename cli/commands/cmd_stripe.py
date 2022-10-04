import click

from libs.util_datetime import tzware_datetime, datetime_to_utc_timestamp
from badmintontv.app import create_app
from badmintontv.extensions import db
from badmintontv.blueprints.billing.gateways.stripecom import Product, Price, TestClock

# Create an app context for the database connection
app = create_app()
db.app = app


@click.group()
def cli():
    '''Perform various tasks with Stripe's API'''
    pass


@click.command()
def sync_plans():
    '''Sync `STRIPE_PRODUCTS` and `STRIPE_PRICES` to Stripe'''
    
    # Exit if there are no plans to sync
    if app.config['STRIPE_PRODUCTS'] is None:
        return None

    # Loop over each product
    for _, value in app.config['STRIPE_PRODUCTS'].items():
        
        id = value['id']
        name = value['name']
        statement_descriptor = value['statement_descriptor']
        
        # If product is not found, create it 
        if not Product.retrieve(id):
            Product.create(
                id=id,
                name=name,
                statement_descriptor=statement_descriptor
            )
            print('Created product id {}'.format(id))
        
        # Otherwise update it 
        else:
            Product.update(
                id=id,
                name=name,
                statement_descriptor=statement_descriptor
            )
            print('Updated product {}'.format(id))
        
    # Loop over each price 
    for _, value in app.config['STRIPE_PRICES'].items():
        
        id = value['id']
        product = value['product']
        nickname = value['name']
        unit_amount = value['amount']
        currency = value['currency']
        billing_scheme = value['billing_scheme']
        recurring = value['recurring']
        
        # If price is not found, create it 
        if not Price.retrieve(id):
            Price.create(
                product=product,
                nickname=nickname,
                unit_amount=unit_amount,
                currency=currency,
                billing_scheme=billing_scheme,
                recurring=recurring
            )
            print('Created price {}'.format(id))
        
        else:
            print('Price already exists: {}'.format(id))


@click.command()
def list_products():
    '''List all existing products on Stripe'''
    click.echo(Product.list())
    

@click.command()
def list_prices():
    '''List all existing prices on Stripe'''
    
    product = app.config['STRIPE_PRODUCTS']['0']['id']
    prices = Price.list(
        product=product
    )
    
    click.echo(prices)
    
    
@click.command()
@click.option('--name', required=True, help='Name of the test clock')
def create_test_clock(name):
    '''Create a new Test Clock with `name`'''
    
    frozen_datetime = tzware_datetime()
    frozen_timestamp = datetime_to_utc_timestamp(frozen_datetime)
    
    test_clock = TestClock.create(
        frozen_time=frozen_timestamp,
        name=name,
    )
    
    click.echo('Test clock created (frozen_time={} ({})):'.format(frozen_timestamp, frozen_datetime))
    click.echo(test_clock)
    click.echo('Remember to save the ID in `/config/settings.py`')
    

@click.command()
def list_test_clocks():
    '''List all Test Clocks'''
    
    test_clocks = TestClock.list()
    
    click.echo(test_clocks)
    

cli.add_command(sync_plans)
cli.add_command(list_products)
cli.add_command(list_prices)
cli.add_command(create_test_clock)
cli.add_command(list_test_clocks)
