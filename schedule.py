from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import client
from functools import wraps
from contextlib import contextmanager
import oauth2client
import datetime
import pickle
import json
import re

with open('settings.json') as f:
    SETTINGS = json.loads(f.read())

@contextmanager
def lazydb(filename):
    with open(filename) as f:
        db = pickle.load(f)

    yield db
    
    with open(filename,'w') as f:
        pickle.dump(db, f)

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

    return datetime.datetime(**dt)

    

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

    creds = client.SignedJwtAssertionCredentials(
            SETTINGS['GSERVEMAIL'],
            private_key,
            SETTINGS['SCOPE'])

    service = build(endpoint, version, http=creds.authorize(Http()))
    return service

def update_calendar(schedule):
    store = []
    calendar = api_service('calendar','v3')
    for i in schedule:
        event = build_event(i['start'],i['end'])
        created = calendar.events().insert(calendarId='primary', body=event).execute()
        i['id'] = created['id']
        store.append(i)
    return store

def display(f):
    """ Wrapper for pyvd display object """
    @wraps(f)
    def wrapper(*args, **kwargs):
        d = Display(visible=0, size=(800,600))
        d.start()
        r = f(*args, **kwargs)
        d.stop()
        return r
    return wrapper

@contextmanager
def driver():
    """ Creates a selenium webdriver object to manipulate """
    b = webdriver.Firefox()
    b.get(SETTINGS['MAIN_URL'])
    yield b
    b.quit()

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
    now = datetime.datetime.now()
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
def get_source(debug=False):
    """ Gets page source for schedule """
    with driver() as browser:
        if debug: print browser.title
        enter_info(browser,
                   SETTINGS['EUID'],
                   SETTINGS['PASSWORD'])
        if debug: print browser.title
        if 'Confirm' in browser.title:
            fix_sessions(browser)
        if debug: print browser.title
        browser.get(SETTINGS['SCHEDULE_URL'])
        if debug: print browser.title
        if 'Confirm' in browser.title:
            fix_sessions(browser)
            if debug: print browser.title
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
    now = datetime.datetime.now()
    schedule = get_schedule()
    
    with lazydb('lazydb.pk') as db:
        for k, v in db.items():
            if v['start'] < now:
                del db[k]
        for k, v in schedule.items():
            if k not in db.keys():
                r = add_event(v)
                db[k] = r




    

