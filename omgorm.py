"""An ORM toolkit for wrapping REST APIs"""
import collections


class Session(object):
    """the context in which resources are used"""

    def __init_subclass__(cls, **kwargs):
        cls.resources = {}
        super().__init_subclass__(**kwargs)

    @classmethod
    def register_resource(cls, resource_cls: type) -> None:
        cls.resources[resource_cls.__name__] = resource_cls


class Field(object):
    """an attribute accessor for a resource"""

    def __set_name__(self, resource, name):
        self.resource, self.name = resource, name


class Resource:
    """base class for API resources"""

    def __init_subclass__(cls, session_cls: type, **kwargs):
        """initialize a Resource subclass

        Parameters
        ----------
        session_cls
            the :class:`Session` subclass to bind to this resource
        """
        session_cls.register_resource(cls)
        cls.session_cls = session_cls
        cls.fields = collections.OrderedDict(
            (name, obj) for name, obj in cls.__dict__.items()
            if isinstance(obj, Field)
        )
        super().__init_subclass__(**kwargs)
