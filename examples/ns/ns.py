import enum
from operator import attrgetter
from datetime import datetime

import snug
import lxml
from snug.utils import partial, compose

parse_datetime = partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%S%z')
parse_bool = dict(true=True, false=False).__getitem__


api = snug.Api('https://webservices.ns.nl/ns-api-',
               parse_response=compose(lxml.etree.fromstring,
                                      attrgetter('content')))


class Station(snug.Resource):
    """a railway station"""
    code = snug.Field('Code/text()')
    type = snug.Field('Type/text()')
    country = snug.Field('Land/text()')
    uic = snug.Field('UICCode/text()')
    lat = snug.Field('Lat/text()')
    lon = snug.Field('Lon/text()')

    name = snug.Field('Namen/Medium/text()')
    full_name = snug.Field('Namen/Lang/text()')
    short_name = snug.Field('Namen/Kort/text()')

    synonyms = snug.Field('Synoniemen/Synoniem/text()', list=True)

    latlon = property(attrgetter('lat', 'lon'))

    def __str__(self):
        country_suffix = f' ({self.country})' if self.country != 'NL' else ''
        return self.full_name + country_suffix


Station.ALL = snug.Collection(
    load=Station.load,
    request=snug.Request('stations-v2')
)


class Departure(snug.Resource):
    """a train departure"""
    ride_number = snug.Field('RitNummer/text()', load=int)
    time = snug.Field(apiname='VertrekTijd/text()', load=parse_datetime)
    delay = snug.Field(apiname='VertrekVertragingTekst/text()', optional=True)
    destination = snug.Field(apiname='EindBestemming/text()')
    train_type = snug.Field(apiname='TreinSoort/text()')
    route_text = snug.Field(apiname='RouteTekst/text()', optional=True)
    carrier = snug.Field(apiname='Vervoerder/text()')
    platform = snug.Field(apiname='VertrekSpoor/text()')
    travel_tip = snug.Field(apiname='ReisTip/text()', optional=True)
    comments = snug.Field(apiname='Opmerkingen/text()', optional=True)

    @staticmethod
    def subset_request(filters):
        return snug.Request('avt', params=filters)

    def __str__(self):
        delaytext = f'[{self.delay}]' if self.delay else ''
        return f'{self.time:%H:%M}{delaytext} - {self.destination}'


class Journey(snug.Resource):
    """a journey option"""

    class Component(snug.Resource):
        """a journey option component"""

        class Status(enum.Enum):
            """status of a journey component"""
            ON_SCHEDULE = 'VOLGENS-PLAN'
            CHANGED = 'GEWIJZIGD'
            CANCELLED = 'GEANNULEERD'
            TRANSFER_NOT_POSSIBLE = 'OVERSTAP-NIET-MOGELIJK'
            DELAYED = 'VERTRAAGD'
            NEW = 'NIEUW'

            def __repr__(self):
                return f'Status.{self.name}'

        class Stop(snug.Resource):
            """a travel stop on a journey component"""

            name = snug.Field('Naam/text()')
            time = snug.Field('Tijd/text()', load=parse_datetime,
                              optional=True)
            delay = snug.Field('VertrekVertraging/text()', optional=True)
            platform = snug.Field('Spoor/text()', optional=True)
            platform_changed = snug.Field('Spoor/@wijziging',
                                          optional=True,
                                          load=parse_bool)

            def __str__(self):
                time = f'{self.time:%H:%M}' if self.time else '??:??'
                delay_text = f'[{self.delay}]' if self.delay else ''
                platform_changed = ' (changed)' if self.platform_changed else''
                platform_text = (f'| platform {self.platform}'
                                 if self.platform else '')
                return (f'{self.name} | {time} {delay_text}'
                        f'{platform_text}{platform_changed}')

        kind = snug.Field('@reisSoort')
        carrier = snug.Field('Vervoerder/text()')
        type = snug.Field('VervoerType/text()')
        ride_number = snug.Field('RitNummer/text()', load=int)
        status = snug.Field('Status/text()', load=Status)
        details = snug.Field('Reisdetails.Reisdetail/text()',
                             load=list,
                             optional=True)
        stops = snug.Field('ReisStop', load=Stop.load, list=True)

        def __str__(self):
            status_suffix = (f' [{self.status.name}]'
                             if self.status is not self.Status.ON_SCHEDULE
                             else '')
            return f'({self.carrier}) {self.type}' + status_suffix

    class Notification(snug.Resource):
        """an notification about a journey option"""
        id = snug.Field('Id/text()', optional=True)
        serious = snug.Field('Ernstig/text()', load=parse_bool)
        text = snug.Field('Text/text()')

        def __str__(self):
            return self.text.upper() if self.serious else self.text

    class Status(enum.Enum):
        """status of a journey option"""
        ON_SCHEDULE = 'VOLGENS-PLAN'
        CHANGED = 'GEWIJZIGD'
        DELAYED = 'VERTRAAGD'
        NEW = 'NIEUW'
        NOT_OPTIMAL = 'NIET-OPTIMAAL'
        NOT_POSSIBLE = 'NIET-MOGELIJK'
        PLAN_CHANGED = 'PLAN-GEWIJZIGD'

        def __repr__(self):
            return f'Status.{self.name}'

    transfer_count = snug.Field('AantalOverstappen/text()')
    planned_duration = snug.Field('GeplandeReisTijd/text()')
    planned_departure = snug.Field('GeplandeVertrekTijd/text()',
                                   load=parse_datetime)
    planned_arrival = snug.Field('GeplandeAankomstTijd/text()',
                                 load=parse_datetime)
    actual_duration = snug.Field('ActueleReisTijd/text()')
    actual_departure = snug.Field('ActueleVertrekTijd/text()',
                                  load=parse_datetime)
    actual_arrival = snug.Field('ActueleAankomstTijd/text()',
                                load=parse_datetime)
    is_optimal = snug.Field('Optimaal/text()', load=parse_bool)
    components = snug.Field('ReisDeel', load=Component.load, list=True)
    notifications = snug.Field('Melding',
                               load=Notification.load, list=True,
                               optional=True)
    status = snug.Field(apiname='Status/text()', load=Status)

    def __str__(self):
        return (f'{self.actual_departure:%H:%M} -> {self.actual_arrival:%H:%M}'
                f' | {self.actual_duration} | {self.transfer_count}'
                + (' (!)' if self.notifications else ''))


class JourneyOptionsQuery(snug.Requestable, snug.utils.Slots):
    start: str
    end: str

    def __request__(self):
        params = dict(zip(('fromStation', 'toStation'), self._astuple()))
        return snug.Request('treinplanner', params=params)

    def __load_response__(self, response):
        return list(map(Journey.load, response))


journey_options = JourneyOptionsQuery
