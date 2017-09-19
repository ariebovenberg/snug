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
    params:  t.Mapping[str, str] = {}
    headers: t.Mapping[str, str] = {}


class Requestable(abc.ABC):
    """mixin for objects which may be requested from an API"""
    __slots__ = ()

    @abc.abstractmethod
    def __request__(self) -> Request:
        raise NotImplementedError()

    @abc.abstractmethod
    def __load_response__(self, response: requests.Response):
        raise NotImplementedError()


class Indexable(abc.ABC):
    """mixin for objects which support item lookup by key"""
    __slots__ = ()

    @abc.abstractmethod
    def load(self, response):
        raise NotImplementedError()

    @abc.abstractmethod
    def item_request(self, key) -> Request:
        raise NotImplementedError()

    @abc.abstractmethod
    def item_connections(self):
        raise NotImplementedError()

    def __getitem__(self, key) -> 'Lookup':
        return Lookup(self, key)


class Filterable(abc.ABC):
    """mixin for objects to support creating filtered subsets"""
    __slots__ = ()

    @abc.abstractmethod
    def load(self, response):
        raise NotImplementedError()

    @abc.abstractmethod
    def subset_request(self, filters) -> Request:
        # TODO: method to validate filters
        raise NotImplementedError()

    def __getitem__(self, filters) -> 'SubSet':
        return SubSet(self, {} if filters == slice(None) else filters)


class Queryable(Indexable, Filterable):
    """an object both indexable and filterable"""
    __slots__ = ()

    def __getitem__(self, key_or_filters):
        super_ = (Filterable if isinstance(key_or_filters, (dict, slice))
                  else Index)
        return super_.__getitem__(self, key_or_filters)


class Lookup(Requestable, utils.Slots):
    """A node selected from an index"""
    index: Indexable
    key:   Key

    def __request__(self):
        return self.index.item_request(self.key)

    def __load_response__(self, obj):
        return self.index.load(obj)

    def __getattr__(self, name):
        try:
            connection = self.index.item_connections[name]
        except KeyError:
            raise AttributeError()
        return connection(self)


class SubSet(Requestable, utils.Slots):
    """A filtered subset"""
    source:  Filterable
    filters: _Filters = {}

    def __request__(self):
        return self.source.subset_request(self.filters)

    def __load_response__(self, objs):
        return list(map(self.source.load, objs))


class Node(Requestable, utils.Slots):
    """a simple, single requestable item"""
    load:        t.Callable
    request:     Request
    connections: t.Mapping[str, t.Callable] = {}

    def __request__(self):
        return self.request

    def __load_response__(self, obj):
        return self.load(obj)

    def __getattr__(self, name):
        try:
            conn = self.connections[name]
        except KeyError:
            raise AttributeError()
        return conn(self)


class FilterableSet(Filterable, utils.Slots):
    """a basic ``Filterable``"""
    load:           t.Callable
    subset_request: t.Callable[[_Filters], Request]

    def __request__(self):
        return self.subset_request({})


class IndexableSet(Indexable, Requestable, utils.Slots):
    request:         Request
    load:            t.Callable
    item_request:    t.Callable
    item_connections: t.Mapping[str, t.Callable] = {}

    def __request__(self):
        return self.request

    def __load_response__(self, response):
        # TODO: generalize
        return list(map(self.load, response))


class QueryableSet(Queryable, Requestable, utils.Slots):
    """a filterable and indexable set"""
    request:          Request
    load:             t.Callable
    item_request:     t.Callable
    subset_request:   t.Callable[[_Filters], Request]
    item_connections: t.Mapping[str, t.Callable] = {}

    def __request__(self):
        return self.request

    def __load_response__(self, response):
        # TODO: generalize
        return list(map(self.load, response))


class Index(Indexable, utils.Slots):
    """a basic ``Indexable``"""
    load:             t.Callable
    item_request:     t.Callable[[Key], Request]
    item_connections: t.Mapping[str, t.Callable] = {}


class Collection(Requestable, utils.Slots):
    """a simple atomic set"""
    load:    t.Callable
    request: Request

    def __request__(self):
        return self.request

    def __load_response__(self, objs):
        return list(map(self.load, objs))


class Connection(utils.Slots):
    func: t.Callable

    def __call__(self, item):
        return self.func(item)


def req(obj: Requestable) -> Request:
    return obj.__request__()


def load(obj: Requestable, response: requests.Response) -> t.Any:
    return obj.__load_response__(response)


class ResourceClass(Queryable, type):
    """Metaclass for resource classes"""

    def __new__(cls, name, bases, dct):
        dct.update({
            'FIELDS': collections.OrderedDict(
                (name, obj) for name, obj in dct.items()
                if isinstance(obj, Field)),
            'item_connections': {
                name: obj for name, obj in dct.items()
                if isinstance(obj, Connection)
            }})
        return super().__new__(cls, name, bases, dct)

    def __repr__(self):
        return f'<resource {self.__module__}.{self.__name__}>'

    def load(self, api_obj) -> 'Resource':
        instance = self.__new__(self)
        instance.api_obj = api_obj
        return instance


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
    optional: bool = False

    def __set_name__(self, resource, name):
        self.resource, self.name = resource, name
        if not self.apiname:
            self.apiname = name

    def __get__(self, instance, cls):
        """part of the descriptor protocol.
        On a class, returns the field.
        On an instance, returns the field value"""
        if instance is None:  # i.e. lookup on class
            return self

        try:
            raw_value = getitem(instance.api_obj, self.apiname)
        except LookupError:
            if self.optional:
                return None
            else:
                raise

        return self.load(raw_value)


class Resource(metaclass=ResourceClass):
    """base class for API resources"""

    def __str__(self):
        return '{0.__class__.__name__} object'.format(self)

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


class Session(utils.Slots):
    """an API session"""
    api:    Api
    auth:   t.Optional[t.Tuple[str, str]] = None
    client: requests.Session = requests.Session()

    def get(self, query: Requestable):
        request = self.api.request(req(query))
        response = self.client.get(request.url,
                                   headers=request.headers,
                                   params=request.params,
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
