country_mapping = {
    'JPN': 'Japan',
    'DEN': 'Denmark',
    'MAS': 'Malaysia',
    'THA': 'Thailand',
    'SGP': 'Singapore',
    'CHN': 'China',
    'IND': 'India',
    'INA': 'Indonesia',
    'VTE': 'Vietnam',
    'USA': 'United States of America',
    'CAD': 'Canada'
}


def format_country(country):
    '''Attempts to convert a short-form country name into its long-form counterpart'''
    if country in country_mapping:
        return country_mapping[country]
    else:
        return country
