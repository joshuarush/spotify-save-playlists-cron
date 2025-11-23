import os
from datetime import date, datetime

#getting env variable along with stripping
def get_env(name):
    if name in os.environ:
        return  os.environ.get(name).strip()
    return None


def get_weekday():
    return date.today().weekday()

def get_timestamp():
    datetime_obj = datetime.now()
    return datetime_obj

def get_time_period():
    """
    Determines the current time period based on hour of day.
    Returns: 'morning', 'afternoon', 'evening', or 'night'

    Time periods:
    - morning: 6am-12pm (6-11)
    - afternoon: 12pm-5pm (12-16)
    - evening: 5pm-9pm (17-20)
    - night: 9pm-6am (21-5)
    """
    hour = datetime.now().hour

    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    else:
        return 'night'