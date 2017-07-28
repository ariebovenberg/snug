"""The core components of the ORM: sessions, resources, and fields"""
import collections
import copy
import itertools
import types
from typing import (Callable, Optional, TypeVar, Union, NamedTuple, Mapping,
                    Tuple, Set)

import requests

from . import utils


__all__ = ['Session', 'Resource', 'Field', 'Api', 'Context', 'wrap_api_obj',
           'Query']


ApiObject = Union[Mapping[str, object]]


class ResourceMeta(utils.EnsurePep487Meta):

    def __getitem__(self, key):
        """return a query of the resource"""
        assert key == slice(None)
        return Query(self)

    def __repr__(self):
        if hasattr(self, 'session'):
            return ('<resource {0.__module__}.{0.__name__} '
                    'bound to {0.session!r}>'.format(self))
        else:
            return '<resource {0.__module__}.{0.__name__}>'.format(self)


class BoundResource(metaclass=utils.EnsurePep487Meta):

    def __init_subclass__(cls, session, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.session = session


Api = NamedTuple('Api', [
    ('headers', Mapping[str, str]),
    ('resources', Set[ResourceMeta]),
])

Context = NamedTuple('Context', [
    ('api', Api),
    ('auth', Optional[Tuple[str, str]]),
])


class Session(metaclass=utils.EnsurePep487Meta):
    """the context in which resources are used"""

    def __init__(self,
                 context: Context,
                 req_session: Optional[requests.Session]=None):
        for resource in context.api.resources:
            name = resource.__name__
            klass = types.new_class(name, bases=(BoundResource, resource),
                                    kwds={'session': self})
            klass.__module__ = resource.__module__
            setattr(self, name, klass)

        self.context = context
        self.req_session = req_session or requests.Session()

    def get(self, url: str) -> requests.Response:
        """perform a GET request. kwargs are passed to the
        underlying requests session
        """
        response = self.req_session.get(
            url,
            headers=self.context.api.headers,
            auth=self.context.auth)
        response.raise_for_status()
        return response

    def __repr__(self):
        return '<Session(context={!r})>'.format(self.context)


class Resource(metaclass=ResourceMeta):
    """base class for API resources"""

    fields = collections.OrderedDict()  # Mapping[str, Field]

    def __init_subclass__(cls, **kwargs):

        # fields from superclasses must be explicitly copied.
        # Otherwise they reference the superclass
        def get_field_copy_linked_to_current_class(field):
            field_copy = copy.copy(field)
            field_copy.__set_name__(cls, field.name)
            return field_copy

        fields_from_superclass = [get_field_copy_linked_to_current_class(f)
                                  for f in cls.fields.values()]

        for field in fields_from_superclass:
            setattr(cls, field.name, field)

        cls.fields = collections.OrderedDict(itertools.chain(
            ((field.name, field) for field in fields_from_superclass),
            ((name, obj) for name, obj in cls.__dict__.items()
             if isinstance(obj, Field))
        ))

    def __str__(self):
        return '[no __str__]'

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


Query = collections.namedtuple('Query', 'resource')


T = TypeVar('T')


def _identity(obj: T) -> T:
    """identity function: returns the input unmodified"""
    return obj


class Field:
    """an attribute accessor for a resource.
    Implements python's descriptor protocol

    Parameters
    ----------
    load
        callable to process a value from an API object to python
    """
    __slots__ = ('name', 'resource', 'load')

    def __init__(self, *, load: Callable[[object], T]=_identity):
        self.load = load

    def __set_name__(self, resource: ResourceMeta, name: str) -> None:
        self.resource, self.name = resource, name

    def __get__(self,
                instance: Optional[Resource],
                cls: ResourceMeta) -> Union['Field', T]:
        """part of the descriptor protocol.
        On a class, returns the field.
        On an instance, returns the field value"""
        return (self
                if instance is None
                else self.load(getitem(instance.api_obj, self.name)))

    def __repr__(self):
        try:
            return ('<Field "{0.name}" of {0.resource!r}>'.format(self))
        except AttributeError:
            return '<Field [no name]>'.format(self)


def getitem(obj, key):
    """get a value from an API object"""
    return obj[key]


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
