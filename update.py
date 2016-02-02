import json
import argparse

from browser import KrogerBrowser
from schedule import update, pull_schedule

with open('data/settings.json') as f:
    SETTINGS = json.loads(f.read())

auth = (SETTINGS['EUID'], SETTINGS['PASSWORD'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Adds kroger work schedule to google calendar')

    parser.add_argument('-i', action='store_true', default=False, help='Interactive prompt')
    parser.add_argument('--calendar', action='store_true', default=False, help='Only updates calendar')
    parser.add_argument('--debug', action='store_true', default=False, help='sets debug state')

    args = parser.parse_args()

    DEBUG = args.debug

    if not args.calendar:
        pull_schedule(*auth, debug = DEBUG)
    update(debug=DEBUG)