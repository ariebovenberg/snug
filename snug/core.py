"""The core components of the ORM: sessions, resources, and fields"""
import collections
import copy
import itertools
import operator
import types
import typing as t
from functools import singledispatch

import requests
import lxml.objectify

from . import utils


__all__ = ['Session', 'Resource', 'Field', 'Api', 'wrap_api_obj', 'Query',
           'Set', 'Node']


ApiObject = t.Union[t.Mapping[str, object],
                    lxml.objectify.ObjectifiedElement]


class Query:
    pass


class Set(t.NamedTuple('_Set', [('resource', 'ResourceMeta')]), Query):
    __slots__ = ()


class Node(t.NamedTuple('_Node', [('resource', 'ResourceMeta'), ('key', str)]),
           Query):
    __slots__ = ()


class ResourceMeta(utils.EnsurePep487Meta):

    def __getitem__(self, key) -> Query:
        """return a query of the resource"""
        if key == slice(None):
            return Set(self)
        else:
            return Node(self, key)

    def __repr__(self):
        if hasattr(self, 'session'):
            return '<bound resource {0.__module__}.{0.__name__}>'.format(self)
        else:
            return '<resource {0.__module__}.{0.__name__}>'.format(self)


class BoundResource(metaclass=utils.EnsurePep487Meta):

    def __init_subclass__(cls, session, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.session = session


Api = t.NamedTuple('Api', [
    ('resources', t.Set[ResourceMeta]),
    ('headers', t.Mapping[str, str]),
    ('create_url', t.Callable[[Query], str]),
    ('parse_response', t.Callable[[Query, requests.Response], object]),
])


class Session(metaclass=utils.EnsurePep487Meta):
    """the context in which an API is used"""

    def __init__(self, api: Api, auth=None,
                 req_session: t.Optional[requests.Session]=None):
        for resource in api.resources:
            name = resource.__name__
            klass = types.new_class(name, bases=(BoundResource, resource),
                                    kwds={'session': self})
            klass.__module__ = resource.__module__
            setattr(self, name, klass)

        self.api = api
        self.auth = auth
        self.req_session = req_session or requests.Session()

    def get(self, query: Query):
        """evaluate the result of a query"""
        response = self.req_session.get(
            self.api.create_url(query),
            headers=self.api.headers,
            auth=self.auth,
        )
        response.raise_for_status()
        return self.api.parse_response(query, response)


class Resource(metaclass=ResourceMeta):
    """base class for API resources"""

    FIELDS = collections.OrderedDict()  # Mapping[str, Field]

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
    __slots__ = ('name', 'resource', 'load', 'apiname')

    def __init__(self, *, load: t.Callable=utils.identity,
                 apiname: t.Optional[str]=None):
        self.load = load
        self.apiname = apiname

    def __set_name__(self, resource: ResourceMeta, name: str) -> None:
        self.resource, self.name = resource, name
        if not self.apiname:
            self.apiname = name

    def __get__(self, instance: t.Optional[Resource], cls: ResourceMeta):
        """part of the descriptor protocol.
        On a class, returns the field.
        On an instance, returns the field value"""
        return (self
                if instance is None
                else self.load(getitem(instance.api_obj, self.apiname)))

    def __repr__(self):
        try:
            return ('<Field "{0.name}" of {0.resource!r}>'.format(self))
        except AttributeError:
            return '<Field [no name]>'.format(self)


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


def wrap_api_obj(resource: ResourceMeta, api_obj: ApiObject) -> Resource:
    """wrap the API object in a resource instance

    Parameters
    ----------
    api_obj
        the API object to wrap

    Returns
    -------
    core.Resource
        the resource instance
    """
    instance = resource.__new__(resource)
    instance.api_obj = api_obj
    return instance
