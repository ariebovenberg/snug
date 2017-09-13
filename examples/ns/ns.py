from operator import attrgetter, methodcaller

import snug
import lxml.objectify
from snug.utils import partial, compose

pyval = attrgetter('pyval')
xmlfield = partial(snug.Field, load=pyval)


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


Station.ALL = snug.Collection(
    load=compose(
        list,
        partial(map, Station.item_load),
        methodcaller('iterchildren'),
    ),
    request=snug.Request('ns-api-stations-v2')
)


api = snug.Api(
    prefix='https://webservices.ns.nl/',
    parse_response=compose(
        lxml.objectify.fromstring,
        attrgetter('content'),
    ),
    resources={Station})
