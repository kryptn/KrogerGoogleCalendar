import re
import json
import pickle
from httplib2 import Http
from functools import wraps
from datetime import datetime
from contextlib import contextmanager

from oauth2client.client import SignedJwtAssertionCredentials
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from pyvirtualdisplay import Display
from apiclient.discovery import build
from bs4 import BeautifulSoup

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

@contextmanager
def driver():
    """ Creates a selenium webdriver object to manipulate """
    try:
        b = webdriver.Firefox()
        b.get(SETTINGS['MAIN_URL'])
        yield b
    finally:
        b.quit()

def display(f):
    """ Wrapper for pyvd display object """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            d = Display(visible=0, size=(800,600))
            d.start()
            r = f(*args, **kwargs)
        finally:
            d.stop()    
        return r
    return wrapper

def make_datetime(dates, times):
    dt = {'year':2015,
          'month':int(dates.split('/')[0]),
          'day':int(dates.split('/')[1])}
    ampm = times[-1]
    times = [int(x) for x in times[:-1].split(':')]
    if ampm == 'p' and times[0] is not 12:
        times[0] = times[0]+12
    elif ampm == 'a' and times[0] is 12:
        times[0] = 0
    dt['hour'] = times[0]
    dt['minute'] = times[1]

    return datetime(**dt)

def build_event(start, end):
    """ Builds calendar object to pass to the api """
    event = {'summary': 'Work',
             'start': {'dateTime': start.isoformat('T'),
                       'timeZone': 'America/Los_Angeles'},
             'end': {'dateTime': end.isoformat('T'),
                     'timeZone': 'America/Los_Angeles'},
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

def enter_info(browser, user, pwd):
    """ Enters relevant info into the login page """
    browser.find_element_by_name('KSWUSER').send_keys(user)
    browser.find_element_by_name('PWD').send_keys(pwd)
    browser.find_element_by_class_name('btn').click()

def fix_sessions(browser):
    """ Attempts to fix a multiple-session error from the Juniper switch """
    browser.find_element_by_name('postfixSID').click()
    browser.find_element_by_name('btnContinue').click()


def parse_calendar(soup):
    """
    Parses the calendar found after logging in
    regex is to get only the day items, which have class%d in their classes
    """
    schema = ('date','time','duration')
    sched = {}
    now = datetime.now()
    for day in soup.find_all('li', class_=re.compile('[1-7]')):
        d = list(day.stripped_strings)
        if len(d) > 1:
            d = dict(zip(schema, d))
            r = {}
            start, end = d['time'].split('-')
            r['start'] = make_datetime(d['date'], start)
            r['end'] = make_datetime(d['date'], end)
            r['id'] = None
            if r['start'] > now:
                sched[d['date']] = r

    return sched

@display
def get_source():
    """ Gets page source for schedule """
    with driver() as browser:
        if DEBUG: print browser.title
        enter_info(browser,
                   SETTINGS['EUID'],
                   SETTINGS['PASSWORD'])
        if DEBUG: print browser.title
        if 'Confirm' in browser.title:
            fix_sessions(browser)
        if DEBUG: print browser.title
        browser.get(SETTINGS['SCHEDULE_URL'])
        if DEBUG: print browser.title
        if 'Confirm' in browser.title:
            fix_sessions(browser)
            if DEBUG: print browser.title
        soup = BeautifulSoup(browser.page_source)
    return soup

def get_schedule():
    soup = get_source()
    schedule = parse_calendar(soup)
    return schedule

def add_event(day):
    calendar = api_service('calendar','v3')
    event = build_event(day['start'],day['end'])
    created = calendar.events().insert(calendarId='primary',body=event).execute()
    day['id'] = created['id']
    return day

def update():
    now = datetime.now()
    schedule = get_schedule()
    
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


    

