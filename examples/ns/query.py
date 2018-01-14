import typing as t
import xml.etree.ElementTree
from datetime import datetime
from operator import attrgetter

import snug
from snug.utils import notnone, valfilter, compose, oneyield

from .load import registry as loads
from .types import Departure, Journey, Station

API_PREFIX = 'https://webservices.ns.nl/ns-api-'
add_prefix = snug.http.prefix_adder(API_PREFIX)
parse_request = compose(xml.etree.ElementTree.fromstring, attrgetter('data'))
basic_interaction = compose(snug.sendmapped(parse_request),
                            snug.yieldmapped(add_prefix),
                            oneyield)

authed_exec = snug.http.authed_exec
authed_aexec = snug.http.authed_aexec


@snug.querytype()
@snug.returnmapped(loads(t.List[Station]))
@basic_interaction
def stations():
    """a list of all stations"""
    return snug.http.GET('stations-v2')


@snug.querytype()
@snug.returnmapped(loads(t.List[Departure]))
@basic_interaction
def departures(station: str):
    """departures for a station"""
    return snug.http.GET('avt', params={'station': station})


@snug.querytype()
@snug.returnmapped(loads(t.List[Journey]))
@basic_interaction
def journey_options(origin:      str,
                    destination: str,
                    via:         t.Optional[str]=None,
                    before:      t.Optional[int]=None,
                    after:       t.Optional[int]=None,
                    time:        t.Optional[datetime]=None,
                    hsl:         t.Optional[bool]=None,
                    year_card:   t.Optional[bool]=None):
    """journey recommendations from an origin to a destination station"""
    return snug.http.GET('treinplanner', params=valfilter(notnone, {
        'fromStation':     origin,
        'toStation':       destination,
        'viaStation':      via,
        'previousAdvices': before,
        'nextAdvices':     after,
        'dateTime':        time,
        'hslAllowed':      hsl,
        'yearCard':        year_card,
    }))
