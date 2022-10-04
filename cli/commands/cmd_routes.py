import click

from badmintontv.app import create_app

app = create_app()


@click.command()
def cli():
    '''
    List all of the available routes

    Returns: String of all routes (path + methods)
    '''
    
    output = {}

    # Loop over all URLs 
    for rule in app.url_map.iter_rules():
        
        # Extact path and methods (ignore blueprint)
        route = {
            'path': rule.rule,
            'methods': '({0})'.format(', '.join(rule.methods))
        }

        # Save route 
        output[rule.endpoint] = route

    # Format using padding 
    endpoint_padding = max(len(endpoint) for endpoint in output.keys()) + 2

    # Sort alphabetically 
    for key in sorted(output):
        
        # Print routes (exclude debug toolbar entries)
        if 'debugtoolbar' not in key and 'debug_toolbar' not in key:
            
            # Left-pad route names with ' '
            click.echo('{0: >{1}}: {2}'.format(
                key, 
                endpoint_padding,
                output[key]
            ))
