import datetime


def hms_to_s(hms):
    '''
    Converts hours-minutes-seconds to seconds 
    
    Params:
        hms (datetime.time)
        
    Returns:
        seconds (int)
    '''
    
    seconds = datetime.timedelta(
        hours=hms.hour,
        minutes=hms.minute,
        seconds=hms.second
    ).total_seconds()
    
    return int(seconds)
