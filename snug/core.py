"""The core components of the ORM: sessions, resources, and fields"""
import abc
import collections
import typing as t
from functools import singledispatch
from operator import attrgetter

import requests
import lxml.objectify

from . import utils


ApiObject = t.Union[t.Mapping[str, object],
                    lxml.objectify.ObjectifiedElement]
Key = t.Union[str, int]
_Filters = t.Mapping[str, t.Any]


class Request(utils.Slots):
    """a simple HTTP request"""
    url:     str
    headers: t.Mapping[str, str] = {}
    params:  t.Mapping[str, str] = {}


class Query(abc.ABC):
    """an API query"""

    @abc.abstractmethod
    def __request__(self) -> Request:
        raise NotImplementedError()

    @abc.abstractmethod
    def __load_response__(self, response):
        raise NotImplementedError()


class Indexable(abc.ABC):
    """an object from which to query a single node"""

    @abc.abstractmethod
    def obj_load(self, response):
        raise NotImplementedError()

    @abc.abstractmethod
    def node_request(self, key) -> Request:
        raise NotImplementedError()

    def __getitem__(self, key) -> 'Node':
        return Node(self, key)


class Filterable(abc.ABC):
    """an object from which to query a set"""

    @abc.abstractmethod
    def list_load(self, response) -> t.List:
        raise NotImplementedError()

    @abc.abstractmethod
    def filtered_request(self, filters) -> Request:
        raise NotImplementedError()

    def __getitem__(self, filters) -> 'FilteredSet':
        return FilteredSet(self, {} if filters == slice(None) else filters)


class ResourceClass(Filterable, Indexable, type):
    """Metaclass for resource classes"""

    def __repr__(self):
        return f'<resource {self.__module__}.{self.__name__}>'

    def obj_load(self, api_obj) -> 'Resource':
        instance = self.__new__(self)
        instance.api_obj = api_obj
        return instance

    def list_load(self, response):
        return list(map(self.obj_load, response))

    def __getitem__(self, key_or_filters):
        super_ = (Filterable if isinstance(key_or_filters, (dict, slice))
                  else Index)
        return super_.__getitem__(self, key_or_filters)


class Set(Query, utils.Slots):
    list_load: t.Callable
    request:   Request

    def __request__(self):
        return self.request

    def __load_response__(self, obj):
        return self.list_load(obj)


class Index(Indexable, utils.Slots):
    """a basic ``Indexable``"""
    obj_load:     t.Callable
    node_request: t.Callable[[Key], Request]


class FilterableSet(Filterable, utils.Slots):
    """a basic ``Filterable``"""
    list_load:        t.Callable
    filtered_request: t.Callable[[_Filters], Request]

    def __request__(self):
        return self.filtered_request({})


class Node(Query, utils.Slots):
    """A node selected from an index"""
    index: Indexable
    key: Key

    def __request__(self):
        return self.index.node_request(self.key)

    def __load_response__(self, obj):
        return self.index.obj_load(obj)


class FilteredSet(Query, utils.Slots):
    """A filtered subset"""
    source:  Filterable
    filters: _Filters = {}

    def __request__(self):
        return self.source.filtered_request(self.filters)

    def __load_response__(self, objs):
        return self.source.list_load(objs)


def req(query) -> Request:
    return query.__request__()


def load(query, response):
    return query.__load_response__(response)


class Api(utils.Slots):
    """an API endpoint"""
    resources:      t.Set[ResourceClass]
    parse_response: t.Callable[[requests.Response], t.Any]
    headers:        t.Mapping[str, str] = {}
    prefix:         str = 'https: //'

    def request(self, request) -> Request:
        return request._replace(
            url=self.prefix + request.url,
            headers={**request.headers, **self.headers},
        )


class Resource(metaclass=ResourceClass):
    """base class for API resources"""

    FIELDS: t.Mapping[str, 'Field'] = collections.OrderedDict()

    def __init_subclass__(cls, **kwargs):
        cls.FIELDS = collections.OrderedDict(
            (name, obj) for name, obj in cls.__dict__.items()
            if isinstance(obj, Field)
        )

    def __str__(self):
        return '{0.__class__.__name__} object'.format(self)

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


class Field(utils.Slots):
    """an attribute accessor for a resource.
    Implements python's descriptor protocol

    Parameters
    ----------
    load
        callable to process a value from an API object to python
    apiname
        the name of the field on the api object
    """
    load:     t.Callable = utils.identity
    apiname:  t.Optional[str] = None
    name:     str = None
    resource: ResourceClass = None

    def __set_name__(self, resource, name):
        self.resource, self.name = resource, name
        if not self.apiname:
            self.apiname = name

    def __get__(self, instance, cls):
        """part of the descriptor protocol.
        On a class, returns the field.
        On an instance, returns the field value"""
        return (self
                if instance is None
                else self.load(getitem(instance.api_obj, self.apiname)))


class Session(utils.Slots):
    """an API session"""
    api:    Api
    auth:   t.Optional[t.Tuple[str, str]] = None
    client: requests.Session = requests.Session()

    def get(self, query: Query):
        request = self.api.request(req(query))
        response = self.client.get(request.url,
                                   headers=request.headers,
                                   auth=self.auth)
        response.raise_for_status()
        response = self.api.parse_response(response)
        return query.__load_response__(response)


@singledispatch
def getitem(obj, key):
    """get a value from an API object"""
    raise TypeError(obj)


@getitem.register(collections.Mapping)
def _mapping_getitem(obj, key):
    return obj[key]


@getitem.register(lxml.objectify.ObjectifiedElement)
def _lxml_getitem(obj, key):
    return attrgetter(key)(obj)
