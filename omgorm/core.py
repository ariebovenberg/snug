"""the core components of the ORM: sessions, resources, and fields"""
import collections
import copy
import itertools
import types

from typing import Mapping

import requests


class Session:
    """the context in which resources are used"""

    def __init__(self):
        for name, resource_class in self.resources.items():
            klass = types.new_class(name, bases=(resource_class, ),
                                    kwds={'session': self})
            klass.__module__ = resource_class.__module__
            setattr(self, name, klass)

        self.requests = requests.Session()

    def __init_subclass__(cls, **kwargs):
        cls.resources: Mapping[str, type] = {}
        super().__init_subclass__(**kwargs)

    @classmethod
    def register_resource(cls, resource_cls: type) -> None:
        cls.resources[resource_cls.__name__] = resource_cls

    def __str__(self):
        return '[no __str__]'

    def __repr__(self):
        return f'<{self.__module__}.{self.__class__.__name__}: {self}>'


class ResourceMeta(type):

    def __repr__(self):
        if hasattr(self, 'session'):
            return (f'<resource {self.__module__}.{self.__name__} '
                    f'bound to {self.session!r}>')
        return f'<resource {self.__module__}.{self.__name__}>'


class Resource(metaclass=ResourceMeta):
    """base class for API resources"""

    fields: Mapping[str, 'Field'] = collections.OrderedDict()

    def __init_subclass__(cls, session_cls: type=None,
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
        elif cls.__bases__ == (Resource, ):
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
        super().__init_subclass__(**kwargs)

    @classmethod
    def wrap_api_obj(cls, api_obj: object) -> 'Resource':
        """wrap the API object in a resource instance

        Parameters
        ----------
        api_obj
            the API object to wrap

        Returns
        -------
        Resource
            the resource instance
        """
        instance = cls.__new__(cls)
        instance.api_obj = api_obj
        return instance

    def __str__(self):
        return '[no __str__]'

    def __repr__(self):
        return f'<{self.__module__}.{self.__class__.__name__}: {self}>'


class Field:
    """an attribute accessor for a resource"""

    def __set_name__(self, resource, name):
        self.resource, self.name = resource, name

    def __get__(self, instance, cls):
        if instance is not None:
            return self.get_value(instance)
        else:
            return self

    def get_value(self, instance: Resource) -> object:  # pragma: no cover
        raise NotImplementedError()

    def to_internal_value(self, value):  # pragma: no cover
        return value

    def __repr__(self):
        try:
            return (f'<{self.__module__}.{self.__class__.__name__} '
                    f'"{self.name}" of {self.resource!r}>')
        except AttributeError:
            return f'<{self.__module__}.{self.__class__.__name__} [no name]>'
