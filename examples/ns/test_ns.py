import json
from pathlib import Path

import snug
import ns

CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

my_ns = snug.Session(api=ns.api, auth=auth)

all_stations = ns.Station.ALL


def test_all_stations():
    assert isinstance(all_stations, snug.Set)
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
