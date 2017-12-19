"""High-level query interface

Todo
----
* serializing query params
* pagination
"""
import abc
import types
import typing as t
from dataclasses import dataclass, field, make_dataclass
from functools import partial, partialmethod

from .abc import Query
from . import http, pipe as pipes
from .utils import (apply, as_tuple, compose, flip, func_to_fields, genresult,
                    identity)

_dictfield = partial(field, default_factory=dict)

__all__ = [
    'Fixed',
    'Nestable',
    'resolve',
    'from_gen',
    'build_resolver',
    'build_async_resolver',
]

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
T_req = t.TypeVar('T_req')
T_resp = t.TypeVar('T_resp')
dclass = partial(dataclass, frozen=True)


@dclass
class Fixed(Query[T, T_req, T_resp]):
    """a static query

    Parameters
    ----------
    request
        the request
    load
        response loader
    """
    request: T_req
    load: t.Callable[[T_resp], T] = identity

    def __resolve__(self):
        return self.load((yield self.request))


class Base(Query[T, T_req, T_resp]):

    @abc.abstractmethod
    def _request(self) -> T_req:
        raise NotImplementedError

    def _parse(self, response: T_resp) -> T:
        return response

    def __resolve__(self):
        return self._parse((yield self._request()))


@dclass
class Wrapped(Query[T, T_req, T_resp]):
    """a query with a pipe modifying requests/responses"""
    pipe:  pipes.Pipe
    inner: Query

    def __resolve__(self):
        resolver = self.inner.__resolve__()
        pipe = self.pipe(next(resolver))
        response = yield next(pipe)
        return resolver.send(genresult(pipe, response))


class NestableMeta(t.GenericMeta):
    """Metaclass for nested queries"""
    # when nested, act like a method.
    # i.e. pass the parent instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Nestable(metaclass=NestableMeta):
    """mixin for classes which behave like methods when called
    (i.e. pass the parent as first argument)"""


def from_gen(func: types.FunctionType) -> t.Type[Query]:
    """create a Query class from a generator function"""
    return make_dataclass(
        func.__name__,
        func_to_fields(func),
        bases=(Query, ),
        namespace={
            '__doc__':     func.__doc__,
            '__module__':  func.__module__,
            '__resolve__': partialmethod(compose(
                partial(apply, func), as_tuple)),
        }
    )


@dclass
class from_requester:
    """create a query class from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    load:   t.Callable
    nestable: bool = False

    def __call__(self, func: types.FunctionType) -> t.Type[Query]:
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Nestable, Base) if self.nestable else (Base, ),
            namespace={
                '__doc__':    func.__doc__,
                '__module__': func.__module__,
                '_request':   partialmethod(compose(
                    partial(apply, func), as_tuple)),
                '_parse':     staticmethod(self.load)
            })


class Authenticator(t.Generic[T_auth]):
    """interface for authenticator callables"""

    @abc.abstractmethod
    def __call__(self, request: http.Request, auth: T_auth) -> http.Request:
        raise NotImplementedError()


Resolver = t.Callable[[Query[T, T_req, T_resp]], T]
"""interface for query resolvers"""

AsyncResolver = t.Callable[[Query[T, T_req, T_resp]], t.Awaitable[T]]
"""interface for asynchronous resolvers"""


def resolve(sender: http.Sender[T_req, T_resp],
            query: Query[T, T_req, T_resp]) -> T:
    res = query.__resolve__()
    response = sender(next(res))
    return genresult(res, response)


async def resolve_async(sender: http.AsyncSender[T_req, T_resp],
                        query: Query[T, T_req, T_resp]) -> t.Awaitable[T]:
    res = query.__resolve__()
    response = await sender(next(res))
    return genresult(res, response)


def build_resolver(
        auth:          T_auth,
        sender:        http.Sender,
        authenticator: Authenticator[T_auth],
        pipe:          pipes.Pipe=pipes.identity) -> Resolver:
    """create an authenticated resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    pipe
        pipe to apply to all requests
    """
    sender = pipes.Sender(sender, pipes.Chain(
        pipe,
        pipes.Preparer(partial(flip(authenticator), auth)),
    ))
    return partial(resolve, sender)


def build_async_resolver(
        auth:          T_auth,
        sender:        http.AsyncSender,
        authenticator: Authenticator[T_auth],
        pipe:          pipes.Pipe=pipes.identity) -> AsyncResolver:
    """create an authenticated, asynchronous, resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    pipe
        pipe to apply to all requests
    """
    sender = pipes.AsyncSender(sender, pipes.Chain(
        pipe,
        pipes.Preparer(partial(flip(authenticator), auth)),
    ))
    return partial(resolve_async, sender)


simple_resolver = partial(
    build_resolver,
    sender=http.urllib_sender(),
    authenticator=lambda r, auth: (r if auth is None
                                   else r.add_basic_auth(auth)),
    pipe=pipes.jsondata,
)
