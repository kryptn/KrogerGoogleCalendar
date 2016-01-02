import json
import argparse
from httplib2 import Http

from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build

from browser import KrogerBrowser
from utils import lazydb

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

def pull_schedule(user,password):
    """
    Pulls the schedule data from the website.

    Part of the user detail pipeline detailed in the README

    """
    browser = KrogerBrowser(user, password,DEBUG=DEBUG)
    browser.pull()

def update():
    """ 
    Updates the user's google calendar with any entry in the lazydb without an
    id set.

    """
    with lazydb('data/lazydb.pk') as db:
        for k, v in db.items():
            if not v['id']:
                if DEBUG: print "Adding new event...",
                result = add_event(v)
                db[k]['id'] = result['id']
                if DEBUG: print "Success", result['id']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Adds kroger work schedule to google calendar')

    parser.add_argument('-i', action='store_true', default=False, help='Interactive prompt')
    parser.add_argument('--calendar', action='store_true', default=False, help='Only updates calendar')
    parser.add_argument('--debug', action='store_true', default=False, help='sets debug state')

    args = parser.parse_args()

    DEBUG = args.debug

    if not args.calendar:
        pull_schedule(SETTINGS['EUID'],SETTINGS['PASSWORD'])
    update()
