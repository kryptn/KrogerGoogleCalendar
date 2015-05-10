import json
from httplib2 import Http
from functools import wraps

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

    creds = SignedJwtAssertionCredentials(SETTINGS['GSERVEMAIL'],
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
    browser = KrogerBrowser(SETTINGS['EUID'], SETTINGS['PASSWORD'],DEBUG=DEBUG)
    browser.pull()
    
    with lazydb('lazydb.pk') as db:

        for k, v in db.items():
            if not v['id']:
                if DEBUG: print "Adding new event...",
                result = add_event(v['start'],v['end'])
                db[k]['id'] = result['id']
                if DEBUG: print "Success", result['id']



DEBUG = True


    

