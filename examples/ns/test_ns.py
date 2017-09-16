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
    assert snug.req(all_stations) == snug.Request('ns-api-stations-v2')

    stations = my_ns.get(all_stations)

    assert isinstance(stations, list)

    amsterdam_stations = [s for s in stations
                          if s.full_name.startswith('Amsterdam')]

    assert len(amsterdam_stations) == 11
    for st in amsterdam_stations:
        print(st)
        print('location: {}'.format(st.latlon))

    den_bosch = stations[0]
    assert len(den_bosch.synonyms) == 2
    print(stations[0].synonyms)


def test_departures():
    assert isinstance(ns.Departure, snug.Filterable)
    assert isinstance(utrecht_departures, snug.SubSet)
    assert snug.req(utrecht_departures) == snug.Request(
        'ns-api-avt', params=dict(station='ut'))

    departures = my_ns.get(utrecht_departures)

    assert len(departures) >= 10
    assert isinstance(departures[0], ns.Departure)
