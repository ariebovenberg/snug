import typing as t
import xml.etree.ElementTree
from datetime import datetime
from functools import partial

import snug
from snug.utils import notnone, valfilter

from .load import registry as loads
from .types import Departure, Journey, Station

API_PREFIX = 'https://webservices.ns.nl/ns-api-'


@snug.wrap.Fixed
def ns_middleware(request):
    """wrapper for all NS requests"""
    response = yield request.add_prefix(API_PREFIX)
    return xml.etree.ElementTree.fromstring(response.data)


resolver = partial(snug.build_resolver,
                   authenticator=snug.Request.add_basic_auth,
                   wrapper=ns_middleware,
                   sender=snug.urllib_sender())

async_resolver = partial(snug.build_async_resolver,
                         authenticator=snug.Request.add_basic_auth,
                         wrapper=ns_middleware)


stations = snug.query.Fixed(snug.Request('stations-v2'),
                            load=loads(t.List[Station]))
"""a list of all stations"""


@snug.query.from_requester(load=loads(t.List[Departure]))
def departures(station: str):
    """departures for a station"""
    return snug.Request('avt', params={'station': station})


@snug.query.from_requester(load=loads(t.List[Journey]))
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
