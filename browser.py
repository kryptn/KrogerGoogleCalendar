import re
from datetime import datetime
from contextlib import contextmanager

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

from utils import make_datetime

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

    def __init__(self, euid, password, **kwargs):
        self.euid = euid
        self.password = password

        if 'main_url' in kwargs.keys():
            self.main_url = kwargs['main_url']

        if 'schedule_url' in kwargs.keys():
            self.schedule_url = kwargs['schedule_url']

    def login(self, browser):
        """ Enters relevant info into the login page """
        browser.find_element_by_name('KSWUSER').send_keys(self.euid)
        browser.find_element_by_name('PWD').send_keys(self.password)
        browser.find_element_by_class_name('btn').click()

    def fix_sessions(self, browser):
        """ Attempts to fix a multiple-session error from the Juniper switch """
        browser.find_element_by_name('postfixSID').click()
        browser.find_element_by_name('btnContinue').click()

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
                start, end = d['time'].split('-')
                r['start'] = make_datetime(d['date'], start)
                r['end'] = make_datetime(d['date'], end)
                r['id'] = None
                if r['start'] > now:
                    sched[d['date']] = r

        return sched

    def navigate(self, browser, url):
        browser.get(url)
        #possible debug statement here

    def get_schedule_source(self):
        with driver() as browser:
            self.navigate(browser, self.main_url)
            self.login(browser)
            if 'Confirm' in browser.title:
                self.fix_sessions(browser)
            self.navigate(browser, self.schedule_url)
            soup = BeautifulSoup(browser.page_source)
        return soup

    def pull(self):
        soup = self.get_schedule_source()
        schedule = self.parse_calendar(soup)
        return schedule
