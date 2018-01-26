import typing as t
import xml.etree.ElementTree
from datetime import datetime
from operator import attrgetter

from gentools import map_return, map_send, map_yield, oneyield, reusable
from toolz import compose, valfilter

import snug

from .load import registry as loads
from .types import Departure, Journey, Station

API_PREFIX = 'https://webservices.ns.nl/ns-api-'
parse_request = compose(xml.etree.ElementTree.fromstring,
                        attrgetter('content'))


def basic_query(returns):
    """decorator factory for NS queries"""
    return compose(
        reusable,
        map_send(parse_request),
        map_yield(snug.prefix_adder(API_PREFIX)),
        map_return(loads(returns)),
        oneyield,
    )


@basic_query(t.List[Station])
def stations():
    """a list of all stations"""
    return snug.GET('stations-v2')


@basic_query(t.List[Departure])
def departures(station: str):
    """departures for a station"""
    return snug.GET('avt', params={'station': station})


@basic_query(t.List[Journey])
def journey_options(origin:      str,
                    destination: str,
                    via:         t.Optional[str]=None,
                    before:      t.Optional[int]=None,
                    after:       t.Optional[int]=None,
                    time:        t.Optional[datetime]=None,
                    hsl:         t.Optional[bool]=None,
                    year_card:   t.Optional[bool]=None):
    """journey recommendations from an origin to a destination station"""
    return snug.GET('treinplanner',
                    params=valfilter(lambda x: x is not None, {
                        'fromStation':     origin,
                        'toStation':       destination,
                        'viaStation':      via,
                        'previousAdvices': before,
                        'nextAdvices':     after,
                        'dateTime':        time,
                        'hslAllowed':      hsl,
                        'yearCard':        year_card,
                    }))
