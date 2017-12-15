import aiohttp
import json
from pathlib import Path

import pytest
import snug
from dataclasses import replace

import ns

live = pytest.config.getoption('--live')
CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = json.loads(CRED_PATH.read_bytes())

# resolve = ns.async_resolver(auth=auth)

all_stations = ns.stations
departures = ns.departures(station='amsterdam')
travel_options = ns.journey_options(origin='breda', destination='amsterdam')
travel_options_no_hsl = replace(travel_options, hsl='false')


@pytest.fixture(scope='module')
async def resolver():
    async with aiohttp.ClientSession() as client:
        yield ns.async_resolver(
            auth=auth,
            sender=snug.http.aiohttp_sender(client)
        )


@pytest.mark.asyncio
async def test_all_stations(resolver):
    assert isinstance(all_stations, snug.Query)

    if live:
        stations = await resolver(all_stations)

        assert isinstance(stations, list)

        amsterdam_stations = [s for s in stations
                              if s.full_name.startswith('Amsterdam')]
        assert len(amsterdam_stations) == 11

        den_bosch = stations[0]
        assert den_bosch.synonyms == ["Hertogenbosch ('s)", 'Den Bosch']


@pytest.mark.asyncio
async def test_departures(resolver):
    assert isinstance(departures, snug.Query)

    if live:
        deps = await resolver(departures)

        assert len(deps) >= 10
        departure = deps[0]
        assert isinstance(departure, ns.Departure)


@pytest.mark.asyncio
async def test_journey_options(resolver):
    assert isinstance(travel_options, snug.Query)

    if live:
        options = await resolver(travel_options)
        assert len(options) >= 10
        assert isinstance(options[0], ns.Journey)

    assert isinstance(travel_options_no_hsl, snug.Query)
    assert travel_options_no_hsl._request() == snug.Request(
        'treinplanner',
        params={'fromStation': 'breda',
                'toStation': 'amsterdam',
                'hslAllowed': 'false'}
    )
