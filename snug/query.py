"""High-level query interface

Todo
----
* serializing query params
* pagination
"""
import abc
import types
import typing as t
from functools import partial, partialmethod

from dataclasses import dataclass, field, astuple, make_dataclass

from . import http, load as loader, wrap
from .utils import apply, genresult, func_to_fields, flip, identity, compose

_dictfield = partial(field, default_factory=dict)

__all__ = [
    'Query',
    'Static',
    'Nested',
    'resolve',
    'gen',
    'build_resolver',
    'build_async_resolver',
]

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


class Base(Query[T]):

    @abc.abstractmethod
    def _request(self):
        raise NotImplementedError

    def _parse(self, response):
        return response

    def __resolve__(self):
        return self._parse((yield self._request()))


@dclass
class Wrapped(Query[T]):
    inner: Query
    wrapper: wrap.Wrapper

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
    """create a Query subclass from a generator function"""
    return make_dataclass(
        func.__name__,
        func_to_fields(func),
        bases=(Query, ),
        namespace={
            '__doc__': func.__doc__,
            '__module__': func.__module__,
            '__resolve__': partialmethod(compose(
                partial(apply, func), astuple)),
        }
    )


def request(func: types.FunctionType) -> t.Type[Query]:
    """create a query class from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    return make_dataclass(
        func.__name__,
        func_to_fields(func),
        bases=(Base, ),
        namespace={
            '__doc__':         func.__doc__,
            '__module__':      func.__module__,
            '_request': partialmethod(compose(
                partial(apply, func), astuple)),
        })


class Authenticator(t.Generic[T_auth]):
    """interface for authenticator callables"""

    @abc.abstractmethod
    def __call__(self, request: http.Request, auth: T_auth) -> http.Request:
        raise NotImplementedError()


Resolver = t.Callable[[Query[T]], T]
"""interface for query resolvers"""

AsyncResolver = t.Callable[[Query[T]], t.Awaitable[T]]
"""interface for asynchronous resolvers"""


def resolve(sender: http.Sender, query: Query[T]) -> T:
    res = query.__resolve__()
    response = sender(next(res))
    return genresult(res, response)


async def resolve_async(sender: http.AsyncSender,
                        query: Query[T]) -> t.Awaitable[T]:
    res = query.__resolve__()
    response = await sender(next(res))
    return genresult(res, response)


def build_resolver(
        auth:          T_auth,
        sender:        http.Sender,
        authenticator: Authenticator[T_auth],
        wrapper:       wrap.Wrapper=wrap.Chain()) -> Resolver:
    """create an authenticated resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    wrapper
        wrapper to apply to all requests
    """
    sender = wrap.Sender(sender, wrap.Chain([
        wrapper,
        wrap.Preparer(partial(flip(authenticator), auth)),
    ]))
    return partial(resolve, sender)


def build_async_resolver(
        auth:          T_auth,
        sender:        http.AsyncSender,
        authenticator: Authenticator[T_auth],
        wrapper:       wrap.Wrapper=wrap.Chain()) -> AsyncResolver:
    """create an authenticated, asynchronous, resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    wrapper
        wrapper to apply to all requests
    """
    sender = wrap.AsyncSender(sender, wrap.Chain([
        wrapper,
        wrap.Preparer(partial(flip(authenticator), auth)),
    ]))
    return partial(resolve_async, sender)


simple_resolver = partial(
    build_resolver,
    sender=http.urllib_sender(),
    authenticator=lambda r, auth: (r if auth is None
                                   else r.add_basic_auth(auth)),
    wrapper=wrap.jsondata,
)
