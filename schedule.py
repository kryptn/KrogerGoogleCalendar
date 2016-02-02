import json
import argparse
from httplib2 import Http

from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build
from pantry import pantry

from browser import KrogerBrowser

with open('data/settings.json') as f:
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
    with open('data/'+SETTINGS['P12_KEY_FILE']) as f:
        private_key = f.read()

    creds = SignedJwtAssertionCredentials(SETTINGS['GSERVEMAIL'],
                                          private_key,
                                          SETTINGS['SCOPE'])

    service = build(endpoint, version, http=creds.authorize(Http()))
    return service

def add_event(day):
    """ Adds json event built by `build_event` to the google calendar """
    calendar = api_service('calendar','v3')
    event = build_event(day['start'],day['end'])
    created = calendar.events().insert(calendarId='primary',body=event).execute()
    day['id'] = created['id']
    return day

def pull_schedule(user,password,debug):
    """
    Pulls the schedule data from the website.

    Part of the user detail pipeline detailed in the README

    """
    browser = KrogerBrowser(user, password,DEBUG=debug)
    browser.pull()

def update(debug=None):
    """ 
    Updates the user's google calendar with any entry in the lazydb without an
    id set.

    """
    with pantry('data/lazydb.pk') as db:
        for k, v in db.items():
            if not v['id']:
                if debug: print "Adding new event...",
                result = add_event(v)
                db[k]['id'] = result['id']
                if debug: print "Success", result['id']
