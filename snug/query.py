"""High-level query interface

Todo
----
* serializing query params
* pagination
* wrapping
* query as generator?
"""
import abc
import inspect
import json
import types
import typing as t
from functools import partial, partialmethod
from operator import methodcaller, attrgetter

from dataclasses import dataclass, field, astuple
from toolz import identity, compose

from . import http, load as loader
from .wrap import Wrapper
from .utils import apply, genresult

_dictfield = partial(field, default_factory=dict)

__all__ = ['Query', 'Static', 'Nested', 'resolve', 'Api', 'simple_resolve',
           'request', 'gen']

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
dclass = partial(dataclass, frozen=True)


class Query(t.Generic[T]):
    """interface for query-like objects.
    Any object with ``__resolve__`` implements it"""

    @abc.abstractmethod
    def __resolve__(self) -> t.Generator[http.Request, http.Response, T]:
        raise NotImplementedError()


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

    def __resolve__(self):
        return self.load((yield self.request))


@dclass
class Wrapped(Query[T]):
    inner: Query
    wrapper: Wrapper

    def __resolve__(self):
        resolver = self.inner.__resolve__()
        wrapper = self.wrapper.__wrap__(next(resolver))
        response = yield next(wrapper)
        return resolver.send(genresult(wrapper, response))


class NestedMeta(t.GenericMeta):
    """Metaclass for nested queries"""
    # when nested, act like a method.
    # i.e. pass the parent instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Nested(Query[T], metaclass=NestedMeta):
    """base class for nested queries"""
    @abc.abstractmethod
    def __resolve__(self):
        raise NotImplementedError()


def gen(func: types.FunctionType) -> t.Type[Query]:
    args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)
    return dataclass(
        types.new_class(
            func.__name__,
            bases=(Query, ),
            exec_body=methodcaller('update', {
                '__annotations__': annotations,
                '__doc__':         func.__doc__,
                '__module__':      func.__module__,
                '__resolve__':         partialmethod(compose(
                    partial(apply, func), astuple)),
                **dict(zip(reversed(args), reversed(defaults or ())))
            })
        ), frozen=True)


@dclass
class Api(Wrapper, t.Generic[T_auth]):
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

    def __wrap__(self, request):
        return self.parse((yield self.prepare(request)))


def request(func: types.FunctionType) -> t.Type[Query]:
    """create a query class from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)

    def mygen(self):
        return (yield func(*astuple(self)))

    return dataclass(
        types.new_class(
            func.__name__,
            bases=(Query, ),
            exec_body=methodcaller('update', {
                '__annotations__': annotations,
                '__doc__':         func.__doc__,
                '__module__':      func.__module__,
                '__resolve__':     mygen,
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
    query = Wrapped(query, api)
    resolver = query.__resolve__()
    request = api.add_auth(next(resolver), auth)
    response = sender(request)
    return genresult(resolver, response)


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
