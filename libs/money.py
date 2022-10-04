def cents_to_dollars(cents):
    '''
    Convert cents to dollars

    Params: 
        cents (int): Amount in cents
        
    Returns: Dollars (float)
    '''
    return round(cents / 100.0, 2)


def dollars_to_cents(dollars):
    '''
    Convert dollars to cents

    Params: 
        dollars (int): Amount in dollars
    
    Returns: Cents (int)
    '''
    return int(dollars * 100)
