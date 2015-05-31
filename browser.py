import re
from datetime import datetime
from contextlib import contextmanager

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from selenium import webdriver

from utils import make_datetime, lazydb

@contextmanager
def driver():

    """ Context manager for both the selenium webdriver
    and the pyvd display instance 

    """

    try:
        display = Display(visible=0, size=(800,600))
        display.start()
        browser = webdriver.Firefox()
        yield browser
    finally:
        browser.quit()
        display.stop()


class KrogerBrowser(object):

    main_url = 'http://greatpeople.me'
    schedule_url = 'https://vpnb-cdc.kroger.com/EmpowerESS/,DanaInfo=wfm.kroger.com+Schedule.aspx'
    DEBUG = False

    def __init__(self, euid, password, **kwargs):
        self.euid = euid
        self.password = password

        if 'main_url' in kwargs.keys():
            self.main_url = kwargs['main_url']

        if 'schedule_url' in kwargs.keys():
            self.schedule_url = kwargs['schedule_url']

        if 'DEBUG' in kwargs.keys():
            self.DEBUG = True

    def login(self, browser):
        """ Enters relevant info into the login page """
        browser.find_element_by_name('KSWUSER').send_keys(self.euid)
        browser.find_element_by_name('PWD').send_keys(self.password)
        browser.find_element_by_class_name('btn').click()

    def fix_sessions(self, browser):
        """ Attempts to fix a multiple-session error from the Juniper switch """
        browser.find_element_by_name('postfixSID').click()
        browser.find_element_by_name('btnContinue').click()

    def navigate(self, browser, url):
        browser.get(url)
        if self.DEBUG:
            print browser.title

    def parse_calendar(self, soup):
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
                if '-' in d['time']: #make sure there's actually a scheduled day
                    start, end = d['time'].split('-')
                    r['start'] = make_datetime(d['date'], start)
                    r['end'] = make_datetime(d['date'], end)
                    r['duration'] = d['duration']
                    r['id'] = None
                    if r['start'] > now:
                        sched[d['date']] = r

        return sched

    def get_schedule_source(self):
        with driver() as browser:
            self.navigate(browser, self.main_url)
            self.login(browser)
            if 'Confirm' in browser.title:
                self.fix_sessions(browser)
            self.navigate(browser, self.schedule_url)
            soup = BeautifulSoup(browser.page_source)
        return soup

    def update_schedule(self, schedule):
        now = datetime.now()
        
        with lazydb('lazydb.pk') as db:
            for k, v in db.items():
                if v['start'] < now:
                    if self.DEBUG: print "Old event removed", v['start']
                    del db[k]
            for k, v in schedule.items():
                if k not in db.keys():
                    if self.DEBUG: print "New event inserted", v['start']
                    db[k] = v
                else:
                    if self.DEBUG: print "Event exists", db[k]['start']

    def pull(self):
        self.soup = self.get_schedule_source()
        self.schedule = self.parse_calendar(self.soup)
        self.update_schedule(self.schedule)
