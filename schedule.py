import json
import pickle
from httplib2 import Http
from functools import wraps
from datetime import datetime
from contextlib import contextmanager

from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build

from browser import KrogerBrowser

with open('settings.json') as f:
    SETTINGS = json.loads(f.read())

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

def build_event(start, end):
    """ Builds calendar object to pass to the api """
    event = {'summary': 'Work',
             'location': SETTINGS['LOCATION']
             'start': {'dateTime': start.isoformat('T'),
                       'timeZone': SETTINGS['TIMEZONE']},
             'end': {'dateTime': end.isoformat('T'),
                     'timeZone': SETTINGS['TIMEZONE']},
             'attendees': [{'email': SETTINGS['EMAIL'],
                            'responseStatus': 'accepted'},],
             }
    return event

def api_service(endpoint, version):
    """ Builds service object to interface with the google api """
    with open(SETTINGS['P12_KEY_FILE']) as f:
        private_key = f.read()

    creds = SignedJwtAssertionCredentials(
            SETTINGS['GSERVEMAIL'],
            private_key,
            SETTINGS['SCOPE'])

    service = build(endpoint, version, http=creds.authorize(Http()))
    return service

def add_event(day):
    calendar = api_service('calendar','v3')
    event = build_event(day['start'],day['end'])
    created = calendar.events().insert(calendarId='primary',body=event).execute()
    day['id'] = created['id']
    return day

def update():
    now = datetime.now()
    browser = KrogerBrowser(SETTINGS['EUID'], SETTINGS['PWD'])
    schedule = browser.pull_schedule()
    
    with lazydb('lazydb.pk') as db:

        for k, v in db.items():
            if v['start'] < now:
                if DEBUG: print "Old event being removed", v['start']
                del db[k]

        for k, v in schedule.items():
            if k not in db.keys():
                r = add_event(v)
                if DEBUG: print "New event inserted", r['start']
                db[k] = r
            else:
                if DEBUG: print "Event already exists", k
DEBUG = True


    

