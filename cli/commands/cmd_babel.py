import os
import click
import subprocess

# Paths
APP_NAME = 'badmintontv'
BABEL_I18N_PATH = os.path.join(APP_NAME, 'translations')
MESSAGES_PATH = os.path.join(APP_NAME, 'translations', 'messages.pot')


@click.group()
def cli():
    '''Manage i18n translations'''
    pass


@click.command()
def extract():
    '''
    Extract text that is marked for translation (by `gettext` and `lazy_gettext`) into a `.pot` file

    Command Params:
        `-F babel.cfg `: Use this config file 
        `-k lazy_gettext`: Also translate from `lazy_gettext` calls 
        `-o {}`: Path to output `.pot` file

    Returns: Subprocess call result
    '''
    babel_cmd = 'pybabel extract -F babel.cfg -k lazy_gettext -o {} {}'.format(MESSAGES_PATH, APP_NAME)
    return subprocess.call(babel_cmd, shell=True)


@click.option('--language', default=None, help='The output language (eg. ko, ja, zh)')
@click.command()
def init(language=None):
    '''
    Map translations to a different language by creating associated `<language>/LC_MESSAGES/______.po` file

    Params:
        `-i {}`: Input `.pot` file
        `-d {}`: Path to translations directory 
        `-l {}`: Langauge (folder name)

    Returns: Subprocess call result
    '''
    babel_cmd = 'pybabel init -i {} -d {} -l {}'.format(MESSAGES_PATH, BABEL_I18N_PATH, language)
    return subprocess.call(babel_cmd, shell=True)


@click.command()
def update():
    '''
    Update all `.po` files with the changes made in the `.pot` file (via `extract()`)
    
    Note: This saves translations added previously (does NOT overwrite work)

    Command Params:
        `-i {}`: Updates phrases listed in this `.pot` file 
        `-d {}`: Path to translations folder 

    Returns: Subprocess call result
    '''
    
    babel_cmd = 'pybabel update -i {} -d {}'.format(MESSAGES_PATH, BABEL_I18N_PATH)
    return subprocess.call(babel_cmd, shell=True)


@click.command()
def compile():
    '''
    Compile new translations into `.mo` files (from each `.po` file)
    
    [?] Remember to remove #, fuzzy lines

    Note: Prior to running this, each translation should be manually placed 
        in its associated `msgstr` variables in the `.po` file

    Command Params:
        `-d {}`: Path to translations folder

    Returns: Subprocess call result
    '''
    babel_cmd = 'pybabel compile -d {}'.format(BABEL_I18N_PATH)
    return subprocess.call(babel_cmd, shell=True)


cli.add_command(extract)
cli.add_command(init)
cli.add_command(compile)
cli.add_command(update)
