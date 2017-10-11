import typing as t
from operator import attrgetter
from datetime import datetime

import snug
import lxml
from dataclasses import dataclass, astuple
from toolz import compose, partial, flip
from snug.utils import filteritems

from . import types

parse_bool = dict(true=True, false=False).__getitem__
parse_datetime = partial(flip(datetime.strptime), '%Y-%m-%dT%H:%M:%S%z')


api = snug.Api('https://webservices.ns.nl/ns-api-',
               parse_response=compose(lxml.etree.fromstring,
                                      attrgetter('content')))


stations = snug.AtomicSet(types.Station, snug.Request('stations-v2'))
"""a list of all stations"""


@dataclass(frozen=True)
class departures(snug.QuerySet, type=types.Departure):
    """departures for a station"""
    station: str

    def __request__(self):
        return snug.Request('avt', params={'station': self.station})


@dataclass(frozen=True)
class journey_options(snug.QuerySet, type=types.Journey):
    start:     str
    end:       str
    via:       t.Optional[str] = None
    before:    t.Optional[int] = None
    after:     t.Optional[int] = None
    time:      t.Optional[datetime] = None
    hsl:       t.Optional[bool] = None
    year_card: t.Optional[bool] = None

    APINAMES = [
        'fromStation',
        'toStation',
        'viaStation',
        'previousAdvices',
        'nextAdvices',
        'dateTime',
        'hslAllowed',
        'yearCard',
    ]

    def __request__(self):
        params = dict(filteritems(zip(self.APINAMES, astuple(self))))
        return snug.Request('treinplanner', params=params)
