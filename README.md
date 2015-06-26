#Kroger Google Calendar#

This script, as it stands right now, will update a user's google calendar with
their relative kroger store's work schedule using greatpeople.me

## Installation ##
On ubuntu/debian systems:
    
    git clone https://github.com/kryptn/KrogerGoogleCalendar.git
    cd KrogerGoogleCalendar
    sudo apt-get install build-essentials libssl-dev libffi-dev python-dev xvfb
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements

## Use ##
    
    python schedule.py [--calendar] [--debug]
