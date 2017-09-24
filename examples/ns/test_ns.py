import json
from pathlib import Path

import snug
import ns

CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

my_ns = snug.Session(api=ns.api, auth=auth)

all_stations = ns.Station.ALL
utrecht_departures = ns.Departure[dict(station='ut')]


def test_all_stations():
    assert isinstance(all_stations, snug.Collection)
    assert snug.req(all_stations) == snug.Request('stations-v2')

    stations = my_ns.get(all_stations)
    print(stations)

    assert isinstance(stations, list)

    amsterdam_stations = [s for s in stations
                          if s.full_name.startswith('Amsterdam')]
    assert len(amsterdam_stations) == 11

    den_bosch = stations[0]
    assert den_bosch.synonyms == ["Hertogenbosch ('s)", 'Den Bosch']


def test_departures():
    assert isinstance(ns.Departure, snug.Filterable)
    assert isinstance(utrecht_departures, snug.SubSet)
    assert snug.req(utrecht_departures) == snug.Request(
        'avt', params=dict(station='ut'))

    departures = my_ns.get(utrecht_departures)

    assert len(departures) >= 10
    print(departures)
    departure = departures[0]
    assert isinstance(departure, ns.Departure)


def test_journey_options():
    options = ns.journey_options(start='breda', end='amsterdam')
    assert isinstance(options, snug.Requestable)
    assert snug.req(options)

    options = my_ns.get(options)
    assert len(options) >= 10
    assert isinstance(options[0], ns.Journey)
