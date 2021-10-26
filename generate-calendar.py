#!/usr/bin/env python3

from datetime import datetime

from icalendar import Calendar, Event

import pytz

events = [x.split(';') for x in open('data').read().splitlines()]

cal = Calendar()
for e in events:
    start = datetime.strptime(e[0], '%d.%m.%Y %H:%M').replace(tzinfo=pytz.timezone('Europe/Prague'))
    event = Event()
    event.add('summary', e[1])
    event.add('dtstart', start)
    cal.add_component(event)

with open('output.ics', 'wb') as f:
    f.write(cal.to_ical())
