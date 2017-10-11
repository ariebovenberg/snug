import json
from pathlib import Path

import pytest

import snug
import ns

CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

my_ns = snug.Session(api=ns.api, auth=auth)

all_stations = ns.stations
utrecht_departures = ns.departures(station='ut')
travel_options = ns.journey_options(start='breda', end='amsterdam')
travel_options_no_hsl = travel_options.select(hsl='false')

live = pytest.config.getoption('--live')


def test_all_stations():
    assert isinstance(all_stations, snug.Set)
    assert snug.req(all_stations) == snug.Request('stations-v2')

    if live:
        stations = my_ns.get(all_stations)

        assert isinstance(stations, list)

        amsterdam_stations = [s for s in stations
                              if s.full_name.startswith('Amsterdam')]
        assert len(amsterdam_stations) == 11

        den_bosch = stations[0]
        assert den_bosch.synonyms == ["Hertogenbosch ('s)", 'Den Bosch']


def test_departures():
    assert isinstance(utrecht_departures, snug.Set)
    assert snug.req(utrecht_departures) == snug.Request(
        'avt', params=dict(station='ut'))

    if live:
        departures = my_ns.get(utrecht_departures)

        assert len(departures) >= 10
        departure = departures[0]
        assert isinstance(departure, ns.Departure)


def test_journey_options():
    assert isinstance(travel_options, snug.Set)
    assert snug.req(travel_options) == snug.Request(
        'treinplanner',
        params={'fromStation': 'breda', 'toStation': 'amsterdam'})

    if live:
        options = my_ns.get(travel_options)
        assert len(options) >= 10
        assert isinstance(options[0], ns.Journey)

        assert isinstance(travel_options_no_hsl, snug.Set)
        assert snug.req(travel_options_no_hsl) == snug.Request(
            'treinplanner',
            params={'fromStation': 'breda',
                    'toStation': 'amsterdam',
                    'hslAllowed': 'false'}
        )
