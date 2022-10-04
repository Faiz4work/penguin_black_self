import os
import binascii
import click


@click.command()
@click.argument('bytes', default=128)
def cli(bytes):
    '''
    Generate a random secret token (for production)

    Returns: Secret token with length `bytes * 2`
    '''
    
    random_bytes = os.urandom(bytes)
    
    # Binary --> Hexadecimal 
    secret_token = binascii.b2a_hex(random_bytes)
    
    # Print 
    return click.echo(secret_token)
