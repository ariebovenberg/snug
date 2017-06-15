"""the core components of the ORM: sessions, resources, and fields"""
import collections
import types


class Session(object):
    """the context in which resources are used"""

    def __init__(self):
        for name, resource_class in self.resources.items():
            klass = types.new_class(name, bases=(resource_class, ),
                                    kwds={'session': self})
            setattr(self, name, klass)

    def __init_subclass__(cls, **kwargs):
        cls.resources: Mapping[str, type] = {}
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
            raise Exception(
                'subclassing ``Resource`` requires a session class')

        if session:
            cls.session = session

        cls.fields = collections.OrderedDict(
            (name, obj) for name, obj in cls.__dict__.items()
            if isinstance(obj, Field)
        )
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
