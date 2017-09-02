import operator
from functools import partial

import snug
import lxml.objectify


API_URL = 'https://webservices.ns.nl/'


pyval = operator.attrgetter('pyval')


class Station(snug.Resource):
    """a railway station"""
    code = snug.Field(apiname='Code', load=pyval)
    type = snug.Field(apiname='Type', load=pyval)
    country = snug.Field(apiname='Land', load=pyval)
    uic = snug.Field(apiname='UICCode', load=pyval)
    lat = snug.Field(apiname='Lat', load=pyval)
    lon = snug.Field(apiname='Lon', load=pyval)

    name = snug.Field(apiname='Namen.Medium', load=pyval)
    full_name = snug.Field(apiname='Namen.Lang', load=pyval)
    short_name = snug.Field(apiname='Namen.Kort', load=pyval)

    synonyms = snug.Field(
        apiname='Synoniemen',
        load=snug.utils.compose(
            list,
            partial(map, pyval),
            operator.methodcaller('iterchildren')))

    latlon = property(operator.attrgetter('lat', 'lon'))

    def __str__(self):
        return self.full_name

    @staticmethod
    def request(selection) -> snug.Request:
        assert isinstance(selection, snug.Set)
        return snug.Request('ns-api-stations-v2')


api = snug.Api(
    prefix='https://webservices.ns.nl/',
    parse_list=snug.utils.compose(
        operator.methodcaller('iterchildren'),
        lxml.objectify.fromstring,
        operator.attrgetter('content'),
    ),
    parse_item=NotImplemented,
    resources={Station})
