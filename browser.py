import re
from datetime import datetime
from contextlib import contextmanager

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from selenium import webdriver
from pantry import pantry


@contextmanager
def driver():

    """ Context manager for both the selenium webdriver
    and the pyvd display instance 

    """

    try:
        display = Display(visible=0, size=(800, 600))
        display.start()
        browser = webdriver.Firefox()
        yield browser
    finally:
        browser.quit()
        display.stop()

def make_datetime(date, time):
    dt = {'year': 2016,
          'month': int(date.split('/')[0]),
          'day': int(date.split('/')[1])}
    ampm = time[-1]
    time = [int(x) for x in time[:-1].split(':')]
    if ampm == 'p' and time[0] is not 12:
        time[0] = time[0]+12
    elif ampm == 'a' and time[0] is 12:
        time[0] = 0
    dt['hour'] = time[0]
    dt['minute'] = time[1]

    return datetime(**dt)


class KrogerBrowser(object):
    """
    Object to handle the browser and selenium driver to simulate logging
    into the website.

    Required arguments:
     - euid: user ID
     - password: password for euid

    Optional arguments:
      - main_url: main page url
      - schedule_url: url for the direct schedule
      - DEBUG: debug boolean

    """

    main_url = 'http://greatpeople.me'
    schedule_url = 'https://vpnb-hdc.kroger.com/EmpowerESS/,DanaInfo=myeschedule.kroger.com+Schedule.aspx'
    DEBUG = False

    def __init__(self, euid, password, **kwargs):
        self.euid = euid
        self.password = password
        self.schedule = {}

        if 'main_url' in kwargs.keys():
            self.main_url = kwargs['main_url']

        if 'schedule_url' in kwargs.keys():
            self.schedule_url = kwargs['schedule_url']

        if 'DEBUG' in kwargs.keys():
            self.DEBUG = True

    def login(self, browser):
        """ 
        Sends user information to the main login page. Information isn't sent anywhere else.

        Final part of the user detail pipeline.

        """
        browser.find_element_by_name('KSWUSER').send_keys(self.euid)
        browser.find_element_by_name('PWD').send_keys(self.password)
        browser.find_element_by_class_name('btn').click()

    def fix_sessions(self, browser):
        """ Attempts to fix a multiple-session error from the Juniper switch """
        browser.find_element_by_name('postfixSID').click()
        browser.implicitly_wait(5)
        browser.find_element_by_name('btnContinue').click()

    def navigate(self, browser, url):
        browser.get(url)
        if self.DEBUG:
            print(browser.title.encode('utf8'))

    def parse_calendar(self):
        """
        Parses the calendar found after logging in
        regex is to get only the day items, which have class%d in their classes
        """
        schema = ('date', 'time')
        now = datetime.now()

        days = self.soup.find_all('li', class_=re.compile('[1-7]'))
        days = [list(x.stripped_strings) for x in days]
        days = [dict(zip(schema,x)) for x in days if len(x) > 1]

        for d in days:
            r = {}
            start, end = d['time'].replace(' ', '').split('-')
            r['start'] = make_datetime(d['date'], start)
            r['end'] = make_datetime(d['date'], end)
            r['id'] = None
            if r['start'] > now:
                self.schedule[d['date']] = r

    def get_schedule_source(self):
        """
        Runs the browser object.

        Logs in, navigates to schedule, scrapes, and closes browser.

        """

        with driver() as browser:
            self.navigate(browser, self.main_url)
            if 'Home' not in browser.title:
                self.login(browser)

            if 'Confirm' in browser.title:
                self.fix_sessions(browser)
            
            self.navigate(browser, self.schedule_url)
            self.soup = BeautifulSoup(browser.page_source)

    def update_schedule(self):
        """
        Updates the lazydb object with newly detected shifts to avoid adding
        already existing shifts to the calendar

        """
        now = datetime.now()

        with pantry('data/lazydb.pk') as db:
            for k, v in db.items():
                if v['start'] < now:
                    if self.DEBUG: print "Old event removed", v['start']
                    del db[k]
            for k, v in self.schedule.items():
                if k not in db.keys():
                    if self.DEBUG: print "New event inserted", v['start']
                    db[k] = v
                else:
                    if self.DEBUG: print "Event exists", db[k]['start']

    def pull(self):
        """ Pulls source, updates into schedule file """
        self.get_schedule_source()
        self.parse_calendar()
        self.update_schedule()
