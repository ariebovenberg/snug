import operator
from functools import singledispatch

import snug
import lxml.objectify


API_URL = 'https://webservices.ns.nl/'


get_pyval = operator.attrgetter('pyval')


class Station(snug.Resource):
    """a railway station"""
    LIST_URI = 'ns-api-stations-v2'

    code = snug.Field(apiname='Code', load=get_pyval)
    type = snug.Field(apiname='Type', load=get_pyval)
    country = snug.Field(apiname='Land', load=get_pyval)
    uic = snug.Field(apiname='UICCode', load=get_pyval)
    lat = snug.Field(apiname='Lat', load=get_pyval)
    lon = snug.Field(apiname='Lon', load=get_pyval)

    name = snug.Field(apiname='Namen.Medium', load=get_pyval)
    full_name = snug.Field(apiname='Namen.Lang', load=get_pyval)
    short_name = snug.Field(apiname='Namen.Kort', load=get_pyval)

    synonyms = snug.Field(
        apiname='Synoniemen',
        load=lambda obj: list(map(get_pyval, obj.iterchildren())))

    latlon = property(operator.attrgetter('lat', 'lon'))

    def __str__(self):
        return self.full_name


@singledispatch
def create_url(query):
    raise TypeError(query)


@create_url.register(snug.Set)
def _create_url_for_set(query):
    return API_URL + query.resource.LIST_URI


@singledispatch
def parse_response(query, response):
    raise TypeError(query)


@parse_response.register(snug.Set)
def _parse_set_response(query, response):
    xml_obj = lxml.objectify.fromstring(response.content)
    return [snug.wrap_api_obj(query.resource, api_obj)
            for api_obj in xml_obj.iterchildren()]


api = snug.Api(headers={},
               create_url=create_url,
               parse_response=parse_response,
               resources={Station})
