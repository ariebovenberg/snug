import json
import requests
import typing as t
from functools import partial
from pathlib import Path

import pytest
import snug
from snug.utils import replace

import ns

live = pytest.config.getoption('--live')
CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = json.loads(CRED_PATH.read_bytes())

resolve = partial(ns.resolve, client=requests.Session(), auth=auth)

all_stations = ns.stations
departures = ns.departures(station='amsterdam')
travel_options = ns.journey_options(origin='breda', destination='amsterdam')
travel_options_no_hsl = replace(travel_options, hsl='false')


def test_all_stations():
    assert isinstance(all_stations, snug.Query)
    assert all_stations.__rtype__ == t.List[ns.Station]
    assert all_stations.__req__ == snug.Request('stations-v2')

    if live:
        stations = resolve(all_stations)

        assert isinstance(stations, list)

        amsterdam_stations = [s for s in stations
                              if s.full_name.startswith('Amsterdam')]
        assert len(amsterdam_stations) == 11

        den_bosch = stations[0]
        assert den_bosch.synonyms == ["Hertogenbosch ('s)", 'Den Bosch']


def test_departures():
    assert isinstance(departures, snug.Query)
    assert departures.__rtype__ == t.List[ns.Departure]
    assert departures.__req__ == snug.Request(
        'avt', params={'station': 'amsterdam'})

    if live:
        deps = resolve(departures)

        assert len(deps) >= 10
        departure = deps[0]
        assert isinstance(departure, ns.Departure)


def test_journey_options():
    assert isinstance(travel_options, snug.Query)
    assert travel_options.__rtype__ == t.List[ns.Journey]
    assert travel_options.__req__ == snug.Request(
        'treinplanner',
        params={'fromStation': 'breda', 'toStation': 'amsterdam'})

    if live:
        options = resolve(travel_options)
        assert len(options) >= 10
        assert isinstance(options[0], ns.Journey)

    assert isinstance(travel_options_no_hsl, snug.Query)
    assert travel_options_no_hsl.__req__ == snug.Request(
        'treinplanner',
        params={'fromStation': 'breda',
                'toStation': 'amsterdam',
                'hslAllowed': 'false'}
    )
