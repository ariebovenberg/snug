import typing as t
from datetime import datetime
from functools import partial
from operator import attrgetter, methodcaller

import snug
import lxml
from toolz import compose, valfilter
from snug.utils import notnone

from .types import Station, Departure, Journey
from .load import load


api = snug.Api(
    prepare=methodcaller('add_prefix', 'https://webservices.ns.nl/ns-api-'),
    parse=compose(lxml.etree.fromstring, attrgetter('content')),
)
resolve = partial(snug.query.resolve, api=api, load=load)

stations = snug.Query(snug.Request('stations-v2'), rtype=t.List[Station])
"""a list of all stations"""


@snug.query.from_func(rtype=t.List[Departure])
def departures(station: str):
    """departures for a station"""
    return snug.Request('avt', params={'station': station})


@snug.query.from_func(rtype=t.List[Journey])
def journey_options(origin:      str,
                    destination: str,
                    via:         t.Optional[str]=None,
                    before:      t.Optional[int]=None,
                    after:       t.Optional[int]=None,
                    time:        t.Optional[datetime]=None,
                    hsl:         t.Optional[bool]=None,
                    year_card:   t.Optional[bool]=None):
    """journey recommendations from an origin to a destination station"""
    return snug.Request('treinplanner', params=valfilter(notnone, {
        'fromStation':     origin,
        'toStation':       destination,
        'viaStation':      via,
        'previousAdvices': before,
        'nextAdvices':     after,
        'dateTime':        time,
        'hslAllowed':      hsl,
        'yearCard':        year_card,
    }))
