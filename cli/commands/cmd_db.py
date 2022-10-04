import click

from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles

from badmintontv.app import create_app
from badmintontv.extensions import db
from badmintontv.blueprints.user.models import User

# Create an app context for the database connection
app = create_app()
db.app = app


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    '''Adds 'CASCADE' to all `db.drop_all()` calls to ensure DB is reset'''
    return compiler.visit_drop_table(element) + " CASCADE"


@click.group()
def cli():
    '''Run PostgreSQL related tasks'''
    pass


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False, help='Create a test database, as well as a production database?')
def init(with_testdb):
    '''
    Initialize the database

    Params:
        with_testdb (bool): Create a test database
    '''
    
    # Purge DB, then re-create it based on our models 
    db.drop_all()
    db.create_all()

    if with_testdb:
        
        # Test DB URI 
        db_uri = '{}_test'.format(app.config['SQLALCHEMY_DATABASE_URI'])

        # If it doesn't exist, create it 
        if not database_exists(db_uri):
            create_database(db_uri)


@click.command()
def seed():
    '''
    Seed the database with an 2 initial users: 1 admin, 1 member 
    
    Email and password defined in:
    - app.config['SEED_ADMIN_EMAIL']
    - app.config['SEED_ADMIN_PASSWORD']
    '''
    
    # If there's already a seed user, abort seeding
    if User.find_by_identity(app.config['SEED_ADMIN_EMAIL']) is not None:
        return None

    # Seed user values 
    params = [
        {
            'role': 'admin',
            'username': app.config['SEED_ADMIN_USERNAME'],
            'email': app.config['SEED_ADMIN_EMAIL'],
            'password': app.config['SEED_ADMIN_PASSWORD'],
            'confirmed': True
        },
        {
            'role': 'member',
            'username': app.config['SEED_MEMBER_USERNAME'],
            'email': app.config['SEED_MEMBER_EMAIL'],
            'password': app.config['SEED_MEMBER_PASSWORD'],
            'confirmed': True
        },
        {
            'role': 'member',
            'username': app.config['SEED_MEMBER_2_USERNAME'],
            'email': app.config['SEED_MEMBER_2_EMAIL'],
            'password': app.config['SEED_MEMBER_2_PASSWORD'],
            'confirmed': True
        }
    ]
    
    # Save users
    for param in params:
        User(**param).save()


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False, help='Create a test database, as well as a production database?')
@click.pass_context            # Allows us to pass in a Click context, which allows us to invoke a different Click command 
def reset(ctx, with_testdb):
    '''
    Initialize the database AND Seed it with an initial admin user
    
    Implementation details in `init()` and `seed()`

    Params:
        with_testdb (bool): Create a test database
    '''
    ctx.invoke(init, with_testdb=with_testdb)
    ctx.invoke(seed)


# Add all commands to CLI
cli.add_command(init)
cli.add_command(seed)
cli.add_command(reset)
