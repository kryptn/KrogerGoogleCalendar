from datetime import datetime
from contextlib import contextmanager
import pickle

@contextmanager
def lazydb(filename):
    # check if file exists
    with open(filename) as f:
        db = pickle.load(f)

    yield db
    
    with open(filename,'w') as f:
        pickle.dump(db, f)

def make_datetime(date, time):
    dt = {'year':2015,
          'month':int(date.split('/')[0]),
          'day':int(date.split('/')[1])}
    ampm = time[-1]
    time = [int(x) for x in time[:-1].split(':')]
    if ampm == 'p' and time[0] is not 12:
        time[0] = time[0]+12
    elif ampm == 'a' and time[0] is 12:
        time[0] = 0
    dt['hour'] = time[0]
    dt['minute'] = time[1]

    return datetime(**dt)