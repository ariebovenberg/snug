from operator import attrgetter, methodcaller
from datetime import datetime

import snug
import lxml.objectify
from snug.utils import partial, compose

pyval = attrgetter('pyval')
xmlfield = partial(snug.Field, load=pyval)
parse_datetime = compose(
    partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%S%z'), pyval)


class Station(snug.Resource):
    """a railway station"""
    code = xmlfield(apiname='Code')
    type = xmlfield(apiname='Type')
    country = xmlfield(apiname='Land')
    uic = xmlfield(apiname='UICCode')
    lat = xmlfield(apiname='Lat')
    lon = xmlfield(apiname='Lon')

    name = xmlfield(apiname='Namen.Medium')
    full_name = xmlfield(apiname='Namen.Lang')
    short_name = xmlfield(apiname='Namen.Kort')

    synonyms = snug.Field(
        apiname='Synoniemen',
        load=snug.utils.compose(
            list,
            partial(map, pyval),
            methodcaller('iterchildren')))

    latlon = property(attrgetter('lat', 'lon'))

    def __str__(self):
        return self.full_name


class Departure(snug.Resource):
    """a train departure"""
    ride_number = xmlfield(apiname='RitNummer')
    time = xmlfield(apiname='VertrekTijd', load=parse_datetime)
    delay = xmlfield(apiname='VertrekVertragingTekst')
    destination = xmlfield(apiname='EindBestemming')
    train_type = xmlfield(apiname='TreinSoort')
    route_text = xmlfield(apiname='RouteTekst')
    carrier = xmlfield(apiname='Vervoerder')
    platform = xmlfield(apiname='VertrekSpoor')
    travel_tip = xmlfield(apiname='ReisTip')
    comments = xmlfield(apiname='Opmerkingen')

    @staticmethod
    def subset_request(filters):
        return snug.Request('ns-api-avt', params=filters)

    def __str__(self):
        try:
            delay = f'[{self.delay}]'
        except Exception:
            delay = ''
        return f'{self.time:%H:%M}{delay} - {self.destination}'


Station.ALL = snug.Collection(
    load=Station.load,
    request=snug.Request('ns-api-stations-v2')
)


api = snug.Api(
    prefix='https://webservices.ns.nl/',
    parse_response=compose(
        methodcaller('iterchildren'),
        lxml.objectify.fromstring,
        attrgetter('content'),
    ),
    resources={Station, Departure})
