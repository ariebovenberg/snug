"""The core components of the ORM: sessions, resources, and fields"""
import collections
import copy
import itertools
import types
from typing import Callable, Optional, TypeVar, Union

import requests

from . import utils


__all__ = ['Session', 'Resource', 'Field']


class Session(metaclass=utils.EnsurePep487Meta):
    """the context in which resources are used"""
    resources = {}

    def __init__(self):
        for name, resource_class in self.resources.items():
            klass = types.new_class(name, bases=(resource_class, ),
                                    kwds={'session': self})
            klass.__module__ = resource_class.__module__
            setattr(self, name, klass)

        self.requests = requests.Session()

    def __init_subclass__(cls, **kwargs):
        cls.resources = {}

    @classmethod
    def register_resource(cls, resource_cls: type) -> None:
        cls.resources[resource_cls.__name__] = resource_cls

    def get(self, url: str, **kwargs) -> requests.Response:
        """perform a GET request. kwargs are passed to the
        underlying requests session
        """
        response = self.requests.get(url, **kwargs)
        response.raise_for_status()
        return response

    def __str__(self):
        return '[no __str__]'

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


class ResourceMeta(utils.EnsurePep487Meta):

    def __repr__(self):
        if hasattr(self, 'session'):
            return ('<resource {0.__module__}.{0.__name__} '
                    'bound to {0.session!r}>'.format(self))
        return '<resource {0.__module__}.{0.__name__}>'.format(self)


class Resource(metaclass=ResourceMeta):
    """base class for API resources"""

    fields = collections.OrderedDict()  # Mapping[str, Field]

    def __init_subclass__(cls, session_cls: type=None,
                          abstract: bool=False,
                          session: Session=None, **kwargs):
        """initialize a Resource subclass

        Parameters
        ----------
        session_cls
            the :class:`Session` subclass to bind to this resource
        session
            the :class:`Session` instance to bind this resource
        """
        if session_cls:
            session_cls.register_resource(cls)
        elif not abstract and cls.__bases__ == (Resource, ):
            raise TypeError(
                'subclassing ``Resource`` requires a session class')

        if session:
            cls.session = session

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

    @classmethod
    def wrap_api_obj(cls, api_obj: object) -> 'Resource':
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
        instance = cls.__new__(cls)
        instance.api_obj = api_obj
        return instance

    def __getitem__(self, key):
        raise NotImplementedError()  # pragma: no cover

    def __str__(self):
        return '[no __str__]'

    def __repr__(self):
        return '<{0.__module__}.{0.__class__.__name__}: {0}>'.format(self)


T = TypeVar('T')


def _identity(obj: T) -> T:
    """identity function: returns the input unmodified"""
    return obj


class Field:
    """an attribute accessor for a resource.
    Implements python's descriptor protocol
    """
    def __init__(self, *, load: Callable[[object], T]=None):
        self.load = load or _identity

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
                else self.load(instance[self.name]))

    def __repr__(self):
        try:
            return ('<{0.__module__}.{0.__class__.__name__} '
                    '"{0.name}" of {0.resource!r}>'.format(self))
        except AttributeError:
            return '<{0.__module__}.{0.__class__.__name__} [no name]>'.format(
                self)
