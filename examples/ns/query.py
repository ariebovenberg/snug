"""the main API"""
import typing as t
import xml.etree.ElementTree
from datetime import datetime
from functools import singledispatch
from operator import attrgetter, methodcaller

from gentools import (compose, map_return, map_send, map_yield, oneyield,
                      reusable)

import snug

from .load import registry as loads
from .types import Departure, Journey, Station

API_PREFIX = 'https://webservices.ns.nl/ns-api-'
parse_request = compose(xml.etree.ElementTree.fromstring,
                        attrgetter('content'))


execute = snug.execute
execute_async = snug.execute_async
executor = snug.executor
async_executor = snug.async_executor


@singledispatch
def dump_param(val):
    """dump a query param value"""
    return str(val)


dump_param.register(datetime, methodcaller('strftime', '%Y-%m-%dT%H:%M'))


def prepare_params(req: snug.Request) -> snug.Request:
    """prepare request parameters"""
    return req.replace(
        params={key: dump_param(val) for key, val in req.params.items()
                if val is not None})


def basic_query(returns):
    """decorator factory for NS queries"""
    return compose(
        reusable,
        map_send(parse_request),
        map_yield(prepare_params, snug.prefix_adder(API_PREFIX)),
        map_return(loads(returns)),
        oneyield,
    )


@basic_query(t.List[Station])
def stations() -> snug.Query[t.List[Station]]:
    """a list of all stations"""
    return snug.GET('stations-v2')


@basic_query(t.List[Departure])
def departures(station: str) -> snug.Query[t.List[Departure]]:
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
                    year_card:   t.Optional[bool]=None) -> (
                        snug.Query[t.List[Journey]]):
    """journey recommendations from an origin to a destination station"""
    return snug.GET('treinplanner', params={
        'fromStation':     origin,
        'toStation':       destination,
        'viaStation':      via,
        'previousAdvices': before,
        'nextAdvices':     after,
        'dateTime':        time,
        'hslAllowed':      hsl,
        'yearCard':        year_card,
    })
