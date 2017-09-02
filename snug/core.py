"""The core components of the ORM: sessions, resources, and fields"""
import abc
import collections
import copy
import itertools
import operator
import typing as t
from functools import singledispatch

import requests
import lxml.objectify
import attr

from . import utils


# __all__ = [
#     'Resource',
#     'Field',
#     'Api',
#     'Selection',
#     'Set',
#     'Node',
#     'Selectable']


ApiObject = t.Union[t.Mapping[str, object],
                    lxml.objectify.ObjectifiedElement]
Key = t.Union[str, int]


class Request(t.NamedTuple):
    """a simple HTTP request"""
    url: str
    headers: t.Mapping[str, str] = {}


class Selection(abc.ABC):
    """mixin for all selections"""

    def request(self) -> Request:
        return self.source.request(self)


class Selectable(abc.ABC):
    """mixin for all things queryable"""

    def __getitem__(self, key) -> Selection:
        return Set(self) if key == slice(None) else Node(self, key)


@Selection.register
class Set(t.NamedTuple):
    """A set selection"""
    source: Selectable

    request = Selection.request

    def wrap(self, api_objs):
        return list(map(self.source.wrap, api_objs))


@Selection.register
class Node(t.NamedTuple):
    """A node selection"""
    source: Selectable
    key: Key

    request = Selection.request

    def wrap(self, api_obj):
        return self.source.wrap(api_obj)


@Selectable.register
class ResourceClass(type):
    """Metaclass for resource classes"""
    __getitem__ = Selectable.__getitem__

    def __repr__(self):
        return f'<resource {self.__module__}.{self.__name__}>'

    def wrap(self, api_obj: ApiObject) -> 'Resource':
        instance = self.__new__(self)
        instance.api_obj = api_obj
        return instance


class Api(t.NamedTuple):
    """an API endpoint"""
    resources: t.Set[ResourceClass]
    parse_list: t.Callable[[requests.Response], t.Any]
    parse_item: t.Callable[[requests.Response], t.Any]
    headers: t.Mapping[str, str] = {}
    prefix: str = 'https://'

    def request(self, request) -> Request:
        return request._replace(
            url=self.prefix + request.url,
            headers={**request.headers, **self.headers},
        )


class Resource(metaclass=ResourceClass):
    """base class for API resources"""

    FIELDS: t.Mapping[str, 'Field'] = collections.OrderedDict()

    def __init_subclass__(cls, **kwargs):

        # fields from superclasses must be explicitly copied.
        # Otherwise they reference the superclass
        def get_field_copy_linked_to_current_class(field):
            field_copy = copy.copy(field)
            field_copy.__set_name__(cls, field.name)
            return field_copy

        fields_from_superclass = [get_field_copy_linked_to_current_class(f)
                                  for f in cls.FIELDS.values()]

        for field in fields_from_superclass:
            setattr(cls, field.name, field)

        cls.FIELDS = collections.OrderedDict(itertools.chain(
            ((field.name, field) for field in fields_from_superclass),
            ((name, obj) for name, obj in cls.__dict__.items()
             if isinstance(obj, Field))
        ))

    def __str__(self):
        return '{0.__class__.__name__} object'.format(self)

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


@attr.s
class Field:
    """an attribute accessor for a resource.
    Implements python's descriptor protocol

    Parameters
    ----------
    load
        callable to process a value from an API object to python
    apiname
        the name of the field on the api object
    """
    load = attr.ib(default=utils.identity)
    apiname = attr.ib(default=None)
    name = attr.ib(init=False)
    resource = attr.ib(init=False)

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


class Session(t.NamedTuple):
    """an API session"""
    api: Api
    auth: t.Optional[t.Tuple[str, str]] = None
    client: requests.Session = requests.Session()

    def get(self, selection: Selection) -> t.Union[Resource, t.List[Resource]]:
        request = self.api.request(selection.request())
        response = self.client.get(request.url,
                                   headers=request.headers,
                                   auth=self.auth)
        response.raise_for_status()
        parse_response = (self.api.parse_list
                          if isinstance(selection, Set)
                          else self.api.parse_item)
        parsed = parse_response(response)
        return selection.wrap(parsed)


@singledispatch
def getitem(obj, key):
    """get a value from an API object"""
    raise TypeError(obj)


@getitem.register(collections.Mapping)
def _mapping_getitem(obj, key):
    return obj[key]


@getitem.register(lxml.objectify.ObjectifiedElement)
def _lxml_getitem(obj, key):
    return operator.attrgetter(key)(obj)
