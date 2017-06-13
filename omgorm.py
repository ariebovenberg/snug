"""An ORM toolkit for wrapping REST APIs"""
import collections


class Field(object):
    """an attribute accessor for a resource"""

    def __set_name__(self, resource, name):
        self.resource, self.name = resource, name


class Resource(object):
    """base class for API resources"""

    def __init_subclass__(cls, **kwargs):
        cls._fields = collections.OrderedDict(
            (name, obj) for name, obj in cls.__dict__.items()
            if isinstance(obj, Field)
        )
