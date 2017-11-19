import typing as t
import xml.etree.ElementTree
from datetime import datetime
from functools import partial
from operator import attrgetter, methodcaller

import requests
from toolz import compose, valfilter

import snug
from snug.utils import notnone

from .types import Station, Departure, Journey
from .load import registry


api = snug.Api(
    prepare=methodcaller('add_prefix', 'https://webservices.ns.nl/ns-api-'),
    parse=compose(xml.etree.ElementTree.fromstring, attrgetter('content')),
    add_auth=snug.Request.add_basic_auth,
)
resolve = partial(
    snug.query.resolve,
    api=api,
    loaders=registry,
    client=requests.Session())

stations = snug.Query(snug.Request('stations-v2'), rtype=t.List[Station])
"""a list of all stations"""


@snug.Query(t.List[Departure])
def departures(station: str):
    """departures for a station"""
    return snug.Request('avt', params={'station': station})


@snug.Query(t.List[Journey])
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
