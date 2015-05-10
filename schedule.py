import json
import pickle
from httplib2 import Http
from functools import wraps
from datetime import datetime

from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build

from browser import KrogerBrowser
from utils import lazydb

with open('settings.json') as f:
    SETTINGS = json.loads(f.read())

def build_event(start, end):
    """ Builds calendar object to pass to the api """
    event = {'summary': 'Work',
             'location': SETTINGS['LOCATION'],
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
    browser = KrogerBrowser(SETTINGS['EUID'], SETTINGS['PASSWORD'])
    schedule = browser.pull()
    
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


    

