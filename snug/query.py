"""High-level query interface

Todo
----
* serializing query params
* pagination
"""
import abc
import inspect
import json
import types
import typing as t
from functools import partial
from operator import methodcaller, attrgetter

from dataclasses import dataclass, field, astuple
from toolz import compose, thread_last, flip

from . import http, load
from .utils import apply

_dictfield = partial(field, default_factory=dict)

__all__ = ['Query', 'resolve', 'Api', 'Querylike', 'simple_resolve']

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')


@dataclass(frozen=True)
class Api(t.Generic[T_auth]):
    """request and response protocols for an API

    Parameters
    ----------
    prepare
        function to prepare requests for sending
    parse
        function to load responses with
    add_auth
        function to apply authentication to a request
    """
    prepare: t.Callable[[http.Request], http.Request]
    parse:   t.Callable[[http.Response], t.Any]
    add_auth: t.Callable[[http.Request, T_auth], http.Request]


class Querylike(t.Generic[T]):
    """interface for query-like objects.
    Any object with ``__req__`` and ``__rtype__`` implements it"""

    @abc.abstractproperty
    def __req__(self) -> http.Request:
        raise NotImplementedError()

    @abc.abstractproperty
    def __rtype__(self) -> t.Type[T]:
        raise NotImplementedError()


class QueryMeta(t.GenericMeta):
    """Metaclass for Query"""

    def __new__(cls, *args, rtype=object):
        created = super().__new__(cls, *args)
        created.__rtype__ = rtype
        return created

    # if the Query is nested, this is reflected in the name
    def __set_name__(self, kls, name):
        self.__name__ = f'{kls.__name__}.{self.__name__}'

    # when nested, act like a method.
    # i.e. pass the parent query instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Query(Querylike[T], metaclass=QueryMeta):
    """A requestable bit of data.
    Can be instatiated, subclassed, or used as a decorator.

    Examples
    --------

    Instantiation results in a static query.

    .. code-block:: python

        latest_post = Query(Request('posts/latest/'), rtype=Post)

    As a decorator, wraps a request-making function in a query subclass.

    .. code-block:: python

        @snug.Query(Post)
        def post(id: int):
            \"\"\"lookup a post by id\"\"\"
            return Request(f'posts/{id}/')

    As a base class, allows more control over query functionality.

    .. code-block:: python

        class post(Query, rtype=Post):
            def __init__(self, id: int):
                ...
            @property
            def __req__(self):
                ...
    """
    def __new__(cls, *args, **kwargs):
        if cls is Query and len(args) < 2 and not kwargs:
            # check if we're being used as a decorator
            if not args:
                return from_request_func()
            elif isinstance(args[0], type):
                return from_request_func(args[0])
            elif isinstance(args[0], types.FunctionType):
                return from_request_func()(args[0])

        return super().__new__(cls)

    def __init__(self, request, rtype=object):
        self.__req__, self.__rtype__ = request, rtype

    __req__ = NotImplemented
    __rtype__ = NotImplemented


@dataclass(frozen=True)
class from_request_func:
    """create a query from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    rtype: type = object

    def __call__(self, func: types.FunctionType):
        args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)
        return dataclass(
            types.new_class(
                func.__name__,
                bases=(Query, ),
                kwds={'rtype': self.rtype},
                exec_body=methodcaller('update', {
                    '__annotations__': annotations,
                    '__doc__':         func.__doc__,
                    '__module__':      func.__module__,
                    '__req__':         property(compose(partial(apply, func),
                                                        astuple)),
                    **dict(zip(reversed(args), reversed(defaults or ())))
                })
            ), frozen=True)


def resolve(query:   Querylike[T],
            api:     Api[T_auth],
            loaders: load.Registry,
            auth:    T_auth,
            sender:  http.Sender) -> T:
    """resolve a querylike object.

    Parameters
    ----------
    query
        the querylike object to evaluate
    api
        the API to handle the request
    loaders
        The registry of object loaders
    auth
        The authentication object
    sender
        The request sender
    """
    return thread_last(
        query,
        attrgetter('__req__'),
        api.prepare,
        (flip(api.add_auth), auth),
        sender,
        api.parse,
        loaders(query.__rtype__))


_simple_json_api = Api(
    prepare=methodcaller('add_prefix', 'https://'),
    parse=compose(json.loads, methodcaller('decode'), attrgetter('content')),
    add_auth=lambda req, auth: (req if auth is None
                                else req.add_basic_auth(auth))
)
simple_resolve = partial(
    resolve,
    api=_simple_json_api,
    loaders=load.simple_registry,
    auth=None,
    sender=http.urllib_sender())
"""a basic resolver"""
