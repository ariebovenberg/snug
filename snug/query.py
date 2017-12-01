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
from toolz import compose, thread_last, flip, identity

from . import http, load as loader
from .utils import apply

_dictfield = partial(field, default_factory=dict)

__all__ = ['Query', 'Static', 'Nested', 'resolve', 'Api', 'simple_resolve',
           'func']

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
dclass = partial(dataclass, frozen=True)


@dclass
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


class Query(t.Generic[T]):
    """interface for query-like objects.
    Any object with ``__req__`` and ``__load__`` implements it"""

    @abc.abstractmethod
    def __req__(self) -> http.Request:
        raise NotImplementedError()

    @staticmethod
    def __load__(response) -> T:
        return response


@dclass
class Static(Query[T]):
    """a static query

    Parameters
    ----------
    request: http.Request
        the http request
    load: load.Loader[T]
        response loader
    """
    request: http.Request
    load: loader.Loader[T] = identity

    def __req__(self):
        return self.request

    __load__ = property(attrgetter('load'))


class NestedMeta(t.GenericMeta):
    """Metaclass for nested queries"""
    # when nested, act like a method.
    # i.e. pass the parent instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Nested(Query[T], metaclass=NestedMeta):
    """base class for nested queries"""
    @abc.abstractmethod
    def __req__(self):
        raise NotImplementedError()


@dclass
class func:
    """create a query from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    load: loader.Loader = identity

    def __call__(self, func: types.FunctionType):
        args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)
        return dataclass(
            types.new_class(
                func.__name__,
                bases=(Query, ),
                exec_body=methodcaller('update', {
                    '__annotations__': annotations,
                    '__doc__':         func.__doc__,
                    '__module__':      func.__module__,
                    '__req__':         property(compose(partial(apply, func),
                                                        astuple)),
                    '__load__':        staticmethod(self.load),
                    **dict(zip(reversed(args), reversed(defaults or ())))
                })
            ), frozen=True)


def resolve(query:   Query[T],
            api:     Api[T_auth],
            auth:    T_auth,
            sender:  http.Sender) -> T:
    """resolve a querylike object.

    Parameters
    ----------
    query
        the querylike object to evaluate
    api
        the API to handle the request
    auth
        The authentication object
    sender
        The request sender
    """
    return thread_last(
        query.__req__,
        api.prepare,
        (flip(api.add_auth), auth),
        sender,
        api.parse,
        query.__load__)


_simple_json_api = Api(
    prepare=methodcaller('add_prefix', 'https://'),
    parse=compose(json.loads, methodcaller('decode'), attrgetter('content')),
    add_auth=lambda req, auth: (req if auth is None
                                else req.add_basic_auth(auth))
)
simple_resolve = partial(
    resolve,
    api=_simple_json_api,
    auth=None,
    sender=http.urllib_sender())
"""a basic resolver"""
