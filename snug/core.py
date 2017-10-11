"""The core components

Todos
-----
* sensibly binding connection classes
* serializing query params
* simple set/item implementations
* ``Response`` object
"""
import collections
import typing as t
from functools import singledispatch, partial

import requests
import lxml.etree
from dataclasses import dataclass, field
from toolz import identity

from .utils import onlyone, replace

_dictfield = partial(field, default_factory=dict)


@dataclass(frozen=True)
class Request:
    """a simple HTTP request"""
    url:     str
    params:  t.Mapping[str, str] = _dictfield()
    headers: t.Mapping[str, str] = _dictfield()


class Requestable:
    """mixin for objects which may be requested from an API"""

    def __request__(self) -> Request:
        raise NotImplementedError()

    def __load_response__(self, response: requests.Response):
        raise NotImplementedError()


class BoundMeta(type):
    """used to bind classes to the parent class in which they are declared"""

    def __set_name__(self, kls, name):
        self.__name__ = f'{kls.__name__}.{self.__name__}'

    def __get__(self, instance, cls):
        """as in a method, pass the current instance as first argument"""
        if instance is None:
            return self
        else:
            return partial(self, instance)


class Item(Requestable, metaclass=BoundMeta):
    """mixin for requestable items"""

    def __init_subclass__(cls, type, **kwargs):
        cls.type = type

    def __load_response__(self, response):
        return self.type.load(response)


class Set(Requestable):
    """mixin for requestable sets"""

    def select(self, **kwargs) -> 'Set':
        return replace(self, **kwargs)

    def __load_response__(self, response):
        return list(map(self.type.load, response))


class QuerySet(Set, metaclass=BoundMeta):

    def __init_subclass__(cls, type, **kwargs):
        cls.type = type


@dataclass(frozen=True)
class AtomicSet(Set):
    type: 'Resource'
    request: Request

    def __request__(self):
        return self.request


def req(obj: Requestable) -> Request:
    """get the request for an object"""
    return obj.__request__()


def load(obj: Requestable, response: requests.Response):
    """load a request result into a query"""
    return obj.__load_response__(response)


class ResourceClass(type):
    """Metaclass for resource classes"""

    def __new__(cls, name, bases, dct):
        dct.update({
            'FIELDS': collections.OrderedDict(
                (name, obj) for name, obj in dct.items()
                if isinstance(obj, Field))})
        return super().__new__(cls, name, bases, dct)

    def __repr__(self):
        return f'<resource {self.__module__}.{self.__name__}>'

    def load(self, api_obj) -> 'Resource':
        instance = self.__new__(self)
        instance.api_obj = api_obj
        return instance


@dataclass(frozen=True)
class Api:
    """an API endpoint"""
    prefix:         str
    parse_response: t.Callable[[requests.Response], t.Any]
    headers:        t.Mapping[str, str] = _dictfield()

    def request(self, request) -> Request:
        return replace(request,
                       url=self.prefix + request.url,
                       headers={**request.headers, **self.headers})


@dataclass
class Field:
    """an attribute accessor for a resource"""
    apiname:  str = None  # if not given, will be set when bound to a class
    load:     t.Callable = identity
    name:     str = None  # set when bound to a class
    optional: bool = False
    list:     bool = False

    def __set_name__(self, resource, name):
        self.name = name
        self.apiname = self.apiname or name

    def __get__(self, instance, cls):
        """On a class, returns the field.
        On an instance, returns the field value"""
        if instance is None:  # i.e. lookup on class
            return self

        try:
            raw_value = getitem(instance.api_obj, self.apiname,
                                aslist=self.list)
        except LookupError:
            if self.optional:
                return None
            else:
                raise

        if self.list:
            return list(map(self.load, raw_value))
        else:
            return self.load(raw_value)


class Resource(metaclass=ResourceClass):
    """base class for API resources"""

    def __str__(self):
        return '{0.__class__.__name__} object'.format(self)

    def __repr__(self):
        return '<{0.__class__.__name__}: {0}>'.format(self)


@dataclass(frozen=True)
class Session:
    """an API session"""
    api:    Api
    auth:   t.Optional[t.Tuple[str, str]] = None
    client: requests.Session = field(default_factory=requests.Session)

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
def getitem(obj, key: str, aslist: bool):
    """get a value from an API object"""
    raise TypeError(obj)


@getitem.register(collections.Mapping)
def _mapping_getitem(obj, key, aslist):
    return obj[key]


@getitem.register(lxml.etree._Element)
def _lxml_getitem(obj, key: str, aslist: bool):
    values = obj.xpath(key)
    if not values:
        raise LookupError(key)
    return values if aslist else onlyone(values)
