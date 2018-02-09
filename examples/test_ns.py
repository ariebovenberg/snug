import json
from pathlib import Path

import aiohttp
import pytest
from gentools import sendreturn

import ns
import snug

live = pytest.config.getoption('--live')
CRED_PATH = Path('~/.snug/ns.json').expanduser()
auth = json.loads(CRED_PATH.read_bytes())


@pytest.fixture(scope='module')
async def exec():
    async with aiohttp.ClientSession() as client:
        yield ns.async_executor(auth=auth, client=client)


@pytest.mark.asyncio
async def test_all_stations(exec):
    all_stations = ns.stations()

    if live:
        stations = await exec(all_stations)
        assert isinstance(stations, list)

        amsterdam_stations = [s for s in stations
                              if s.full_name.startswith('Amsterdam')]
        assert len(amsterdam_stations) == 11

        den_bosch = stations[0]
        assert den_bosch.synonyms == ["Hertogenbosch ('s)", 'Den Bosch']

    # offline test
    query = iter(all_stations)
    assert next(query).url.endswith('stations-v2')
    result = sendreturn(query, snug.Response(200, content=STATIONS_SAMPLE))
    assert len(result) == 4
    assert result[3].full_name == 'Aachen Hbf'


@pytest.mark.asyncio
async def test_departures(exec):
    departures = ns.departures(station='Amsterdam')

    if live:
        deps = await exec(departures)

        assert len(deps) >= 10
        departure = deps[0]
        assert isinstance(departure, ns.Departure)

    # offline test
    query = iter(departures)
    req = next(query)
    assert req.url.endswith('avt')
    assert req.params == {'station': 'Amsterdam'}
    result = sendreturn(query, snug.Response(200, content=DEPARTURES_SAMPLE))
    assert len(result)
    assert result[1].platform_changed


@pytest.mark.asyncio
async def test_journey_options(exec):
    travel_options = ns.journey_options(origin='Breda',
                                        destination='Amsterdam')
    travel_options_no_hsl = travel_options.replace(hsl='false')

    if live:
        options = await exec(travel_options)
        assert len(options) >= 10
        assert isinstance(options[0], ns.Journey)

    # offline test
    query = iter(travel_options)
    assert next(query).params == {'fromStation': 'Breda',
                                  'toStation': 'Amsterdam'}
    result = sendreturn(query, snug.Response(200, content=JOURNEYS_SAMPLE))
    assert len(result) == 3
    assert result[0].components[1].stops[-1].platform == '8a'

    assert next(iter(travel_options_no_hsl)).params == {
        'fromStation': 'Breda',
        'toStation': 'Amsterdam',
        'hslAllowed': 'false'}


STATIONS_SAMPLE = b'''\
<Stations>
    <Station>
        <Code>HT</Code>
        <Type>knooppuntIntercitystation</Type>
        <Namen>
          <Kort>Den Bosch</Kort>
          <Middel>'s-Hertogenbosch</Middel>
          <Lang>'s-Hertogenbosch</Lang>
        </Namen>
        <Land>NL</Land>
        <UICCode>8400319</UICCode>
        <Lat>51.69048</Lat>
        <Lon>5.29362</Lon>
        <Synoniemen>
            <Synoniem>Hertogenbosch ('s)</Synoniem>
            <Synoniem>Den Bosch</Synoniem>
        </Synoniemen>
    </Station>
    <Station>
        <Code>HTO</Code>
        <Type>stoptreinstation</Type>
        <Namen>
          <Kort>Dn Bosch O</Kort>
          <Middel>Hertogenb. Oost</Middel>
          <Lang>'s-Hertogenbosch Oost</Lang>
        </Namen>
        <Land>NL</Land>
        <UICCode>8400320</UICCode>
        <Lat>51.700553894043</Lat>
        <Lon>5.3183331489563</Lon>
        <Synoniemen>
            <Synoniem>Hertogenbosch Oost ('s)</Synoniem>
            <Synoniem>Den Bosch Oost</Synoniem>
        </Synoniemen>
    </Station>
    <Station>
        <Code>HDE</Code>
        <Type>stoptreinstation</Type>
        <Namen>
          <Kort>'t Harde</Kort>
          <Middel>'t Harde</Middel>
          <Lang>'t Harde</Lang>
        </Namen>
        <Land>NL</Land>
        <UICCode>8400388</UICCode>
        <Lat>52.4091682</Lat>
        <Lon>5.893611</Lon>
        <Synoniemen>
            <Synoniem>Harde ('t)</Synoniem>
        </Synoniemen>
    </Station>
    <Station>
        <Code>AHBF</Code>
        <Type>knooppuntIntercitystation</Type>
        <Namen>
          <Kort>Aachen</Kort>
          <Middel>Aachen Hbf</Middel>
          <Lang>Aachen Hbf</Lang>
        </Namen>
        <Land>D</Land>
        <UICCode>8015345</UICCode>
        <Lat>50.7678</Lat>
        <Lon>6.091499</Lon>
        <Synoniemen>
        </Synoniemen>
    </Station>
</Stations>
'''

DEPARTURES_SAMPLE = b'''\
<ActueleVertrekTijden>
    <VertrekkendeTrein>
        <RitNummer>2187</RitNummer>
        <VertrekTijd>2018-01-22T21:49:00+0100</VertrekTijd>
        <EindBestemming>Den Haag Centraal</EindBestemming>
        <TreinSoort>Intercity</TreinSoort>
            <RouteTekst>A'dam Sloterdijk, Haarlem, Leiden C.</RouteTekst>
            <Vervoerder>NS</Vervoerder>
        <VertrekSpoor wijziging="false">2a</VertrekSpoor>
    </VertrekkendeTrein>
    <VertrekkendeTrein>
        <RitNummer>4083</RitNummer>
        <VertrekTijd>2018-01-22T21:49:00+0100</VertrekTijd>
        <EindBestemming>Rotterdam Centraal</EindBestemming>
        <TreinSoort>Sprinter</TreinSoort>
            <RouteTekst>Duivendrecht, Bijlmer ArenA, Breukelen</RouteTekst>
            <Vervoerder>NS</Vervoerder>
        <VertrekSpoor wijziging="true">4b</VertrekSpoor>
    </VertrekkendeTrein>
    <VertrekkendeTrein>
        <RitNummer>2974</RitNummer>
        <VertrekTijd>2018-01-22T21:53:00+0100</VertrekTijd>
        <EindBestemming>Enkhuizen</EindBestemming>
        <TreinSoort>Intercity</TreinSoort>
            <RouteTekst>A'dam Sloterdijk, Hoorn</RouteTekst>
            <Vervoerder>NS</Vervoerder>
        <VertrekSpoor wijziging="false">8a</VertrekSpoor>
    </VertrekkendeTrein>
    <VertrekkendeTrein>
        <RitNummer>14681</RitNummer>
        <VertrekTijd>2018-01-22T21:53:00+0100</VertrekTijd>
        <EindBestemming>Zwolle</EindBestemming>
        <TreinSoort>Sprinter</TreinSoort>
            <RouteTekst>Weesp, Lelystad C.</RouteTekst>
            <Vervoerder>NS</Vervoerder>
        <VertrekSpoor wijziging="false">10b</VertrekSpoor>
    </VertrekkendeTrein>
</ActueleVertrekTijden>
'''

JOURNEYS_SAMPLE = b'''\
<ReisMogelijkheden>
  <ReisMogelijkheid>
    <AantalOverstappen>1</AantalOverstappen>
    <GeplandeReisTijd>1:29</GeplandeReisTijd>
    <ActueleReisTijd>1:29</ActueleReisTijd>
    <GeplandeVertrekTijd>2018-01-22T20:20:00+0100</GeplandeVertrekTijd>
    <ActueleVertrekTijd>2018-01-22T20:20:00+0100</ActueleVertrekTijd>
    <GeplandeAankomstTijd>2018-01-22T21:49:00+0100</GeplandeAankomstTijd>
    <ActueleAankomstTijd>2018-01-22T21:49:00+0100</ActueleAankomstTijd>
    <Status>NIEUW</Status>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity</VervoerType>
      <RitNummer>3674</RitNummer>
      <Status>VOLGENS-PLAN</Status>
      <ReisStop>
        <Naam>Breda</Naam>
        <Tijd>2018-01-22T20:20:00+0100</Tijd>
        <Spoor wijziging="false">3</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Tilburg</Naam>
        <Tijd>2018-01-22T20:34:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>'s-Hertogenbosch</Naam>
        <Tijd>2018-01-22T20:49:00+0100</Tijd>
        <Spoor wijziging="false">1</Spoor>
      </ReisStop>
    </ReisDeel>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity</VervoerType>
      <RitNummer>2974</RitNummer>
      <Status>VOLGENS-PLAN</Status>
      <ReisStop>
        <Naam>'s-Hertogenbosch</Naam>
        <Tijd>2018-01-22T20:54:00+0100</Tijd>
        <Spoor wijziging="false">3</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Utrecht Centraal</Naam>
        <Tijd>2018-01-22T21:23:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Amsterdam Amstel</Naam>
        <Tijd>2018-01-22T21:41:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Amsterdam Centraal</Naam>
        <Tijd>2018-01-22T21:49:00+0100</Tijd>
        <Spoor wijziging="false">8a</Spoor>
      </ReisStop>
    </ReisDeel>
  </ReisMogelijkheid>
  <ReisMogelijkheid>
    <Melding>
      <Id></Id>
      <Ernstig>true</Ernstig>
      <Text>Dit reisadvies vervalt</Text>
    </Melding>
    <AantalOverstappen>1</AantalOverstappen>
    <GeplandeReisTijd>1:14</GeplandeReisTijd>
    <ActueleReisTijd>1:14</ActueleReisTijd>
    <Optimaal>false</Optimaal>
    <GeplandeVertrekTijd>2018-01-22T20:23:00+0100</GeplandeVertrekTijd>
    <ActueleVertrekTijd>2018-01-22T20:23:00+0100</ActueleVertrekTijd>
    <GeplandeAankomstTijd>2018-01-22T21:37:00+0100</GeplandeAankomstTijd>
    <ActueleAankomstTijd>2018-01-22T21:37:00+0100</ActueleAankomstTijd>
    <Status>NIET-MOGELIJK</Status>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity</VervoerType>
      <RitNummer>1170</RitNummer>
      <Status>VOLGENS-PLAN</Status>
      <ReisStop>
        <Naam>Breda</Naam>
        <Tijd>2018-01-22T20:23:00+0100</Tijd>
        <Spoor wijziging="false">7</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Rotterdam Centraal</Naam>
        <Tijd>2018-01-22T20:47:00+0100</Tijd>
        <Spoor wijziging="false">9</Spoor>
      </ReisStop>
    </ReisDeel>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity direct</VervoerType>
      <RitNummer>1061</RitNummer>
      <Status>GEANNULEERD</Status>
      <Reisdetails>
        <Reisdetail>Toeslag Schiphol-Rotterdam vv</Reisdetail>
      </Reisdetails>
      <ReisStop>
        <Naam>Rotterdam Centraal</Naam>
        <Tijd>2018-01-22T20:57:00+0100</Tijd>
        <Spoor wijziging="false">12</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Schiphol Airport</Naam>
        <Tijd>2018-01-22T21:23:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Amsterdam Centraal</Naam>
        <Tijd>2018-01-22T21:37:00+0100</Tijd>
        <Spoor wijziging="false">14a</Spoor>
      </ReisStop>
    </ReisDeel>
  </ReisMogelijkheid>
  <ReisMogelijkheid>
    <Melding>
      <Id></Id>
      <Ernstig>false</Ernstig>
      <Text>Dit is een aangepast reisadvies</Text>
    </Melding>
    <AantalOverstappen>1</AantalOverstappen>
    <GeplandeReisTijd>1:47</GeplandeReisTijd>
    <ActueleReisTijd>1:47</ActueleReisTijd>
    <Optimaal>false</Optimaal>
    <GeplandeVertrekTijd>2018-01-22T20:23:00+0100</GeplandeVertrekTijd>
    <ActueleVertrekTijd>2018-01-22T20:23:00+0100</ActueleVertrekTijd>
    <GeplandeAankomstTijd>2018-01-22T22:10:00+0100</GeplandeAankomstTijd>
    <ActueleAankomstTijd>2018-01-22T22:10:00+0100</ActueleAankomstTijd>
    <Status>GEWIJZIGD</Status>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity</VervoerType>
      <RitNummer>1170</RitNummer>
      <Status>VOLGENS-PLAN</Status>
      <ReisStop>
        <Naam>Breda</Naam>
        <Tijd>2018-01-22T20:23:00+0100</Tijd>
        <Spoor wijziging="false">7</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Rotterdam Centraal</Naam>
        <Tijd>2018-01-22T20:48:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Delft</Naam>
        <Tijd>2018-01-22T21:00:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Den Haag HS</Naam>
        <Tijd>2018-01-22T21:08:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Den Haag Centraal</Naam>
        <Tijd>2018-01-22T21:12:00+0100</Tijd>
        <Spoor wijziging="false">1</Spoor>
      </ReisStop>
    </ReisDeel>
    <ReisDeel reisSoort="TRAIN">
      <Vervoerder>NS</Vervoerder>
      <VervoerType>Intercity</VervoerType>
      <RitNummer>2170</RitNummer>
      <Status>VOLGENS-PLAN</Status>
      <ReisStop>
        <Naam>Den Haag Centraal</Naam>
        <Tijd>2018-01-22T21:18:00+0100</Tijd>
        <Spoor wijziging="false">10</Spoor>
      </ReisStop>
      <ReisStop>
        <Naam>Leiden Centraal</Naam>
        <Tijd>2018-01-22T21:35:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Heemstede-Aerdenhout</Naam>
        <Tijd>2018-01-22T21:49:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Haarlem</Naam>
        <Tijd>2018-01-22T21:55:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Amsterdam Sloterdijk</Naam>
        <Tijd>2018-01-22T22:04:00+0100</Tijd>
      </ReisStop>
      <ReisStop>
        <Naam>Amsterdam Centraal</Naam>
        <Tijd>2018-01-22T22:10:00+0100</Tijd>
        <Spoor wijziging="false">7a</Spoor>
      </ReisStop>
    </ReisDeel>
  </ReisMogelijkheid>
</ReisMogelijkheden>
'''
