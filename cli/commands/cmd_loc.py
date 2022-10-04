import click

from subprocess import check_output


def count_locs(file_type, comment_pattern):
    '''
    Detect if a program is on the system path

    Params:
        file_type (str):         Which file type will be searched?
        comment_pattern (str):   Escaped characters that are comments
    
    Returns: Number of lines of code 
    '''
    
    # Find files of type `file_type`
    find = "find . -name '*.{0}' -print0".format(file_type)
    
    # Filter out comments 
    sed_pattern = "'/^\s*{0}/d;/^\s*$/d'".format(comment_pattern)
    
    # Count number of lines 
    cmd = "{0} | xargs -0 sed {1} | wc -l".format(find, sed_pattern)

    # Store into variable 
    return check_output(cmd, shell=True).decode('utf-8').replace('\n', '')


@click.command()
def cli():
    '''
    Count lines of code in the project
    
    Note: This excludes comments (Python) and comments + newlines (HTML, CSS, JS)
    '''
    
    file_types = (
        ['Python', 'py', '#'],
        ['HTML', 'html', '<!--'],
        ['CSS', 'css', '\/\*'],
        ['JS', 'js', '\/\/']
    )

    click.echo('Lines of code\n-------------')

    for file_type in file_types:
        click.echo("{0}: {1}".format(
            file_type[0], 
            count_locs(
                file_type=file_type[1], 
                comment_pattern=file_type[2]
            )
        ))
