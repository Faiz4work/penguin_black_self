import os

import click

# All commands willl be in `./Database/cli/commands` folder
cmd_folder = os.path.join(os.path.dirname(__file__), 'commands')

# Only look for files with this prefix 
cmd_prefix = 'cmd_'


class CLI(click.MultiCommand):
    def list_commands(self, ctx):
        '''
        Obtain a list of all available commands

        Params:
            ctx: Click context
            
        Return: 
            commands (list): List of sorted commands
        '''
        
        commands = []

        # Look for valid commands
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and filename.startswith(cmd_prefix):
                commands.append(filename[4:-3])

        # Sort alphabetically 
        commands.sort()

        return commands

    def get_command(self, ctx, name):
        '''
        Get a specific command by looking up the module
        
        Note: This gets run when a `badmintontv` command is run
        The CLI function of that command will then be executed (`cli(...)` in `cmd_test.py`)

        Params:
            ctx:          Click context
            name (str):   Command name
        
        Return: Module's cli function
        '''
        
        ns = {}

        filename = os.path.join(cmd_folder, cmd_prefix + name + '.py')

        with open(filename) as f:
            code = compile(f.read(), filename, 'exec')
            eval(code, ns, ns)

        return ns['cli']


# Entry point to the CLI app 
# This is used when `badmintontv` is run with no arguments 
@click.command(cls=CLI)
def cli():
    '''Commands to help manage the project'''
    pass
