"""the central abstractions"""
import abc
import typing as t
from dataclasses import make_dataclass
from functools import partial, partialmethod, wraps
from types import GeneratorType

from .utils import (compose, nest, dclass, yieldmap, sendmap, returnmap,
                    func_to_fields, apply, as_tuple)

__all__ = [
    'Query',
    'Sender',
    'Pipe',
    'execute',
    'nested',
    'yieldmapped',
    'sendmapped',
    'returnmapped',
    'query',
]


T = t.TypeVar('T')
T_req = t.TypeVar('T_req')
T_resp = t.TypeVar('T_resp')
T_prepared = t.TypeVar('T_prepared')
T_parsed = t.TypeVar('T_parsed')


class Query(t.Generic[T_req, T_resp, T], t.Iterable[T_req]):
    """ABC for query-like objects.
    Any object where ``__iter__`` returns a generator implements it"""

    @abc.abstractmethod
    def __iter__(self) -> t.Generator[T_req, T_resp, T]:
        """a generator which resolves the query"""
        raise NotImplementedError()


Query.register(GeneratorType)


class Sender(t.Generic[T_req, T_resp]):
    """ABC for sender-like objects.
    Any callable with the same signature implements it"""

    def __call__(self, request: T_req) -> T_resp:
        """send a request, returning a response"""
        raise NotImplementedError()


class Pipe(t.Generic[T_req, T_prepared, T_resp, T_parsed]):
    """ABC for middleware objects.
    generator callables with the same signature implement it."""

    @abc.abstractmethod
    def __call__(self, request: T_req) -> t.Generator[T_prepared,
                                                      T_resp,
                                                      T_parsed]:
        """wrap a request and response"""
        raise NotImplementedError()

    @staticmethod
    def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
        """identity pipe, leaves requests and responses unchanged"""
        return (yield request)


class Executor(t.Generic[T_req, T_resp]):

    @abc.abstractmethod
    def __call__(self, query: Query[T_req, T_resp, T]) -> T:
        raise NotImplementedError()


def execute(query:  Query[T_req, T_resp, T],
            sender: Sender[T_req, T_resp]) -> T:
    """execute a query

    Parameters
    ----------
    query
        the query to resolve
    sender
        the sender to use
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


# TODO: docs, types
@dclass
class nested:
    thru: Pipe

    def __call__(self, func):
        return wraps(func)(compose(partial(nest, pipe=self.thru), func))


# TODO: docs, types
@dclass
class yieldmapped:
    func: t.Callable

    def __call__(self, func):
        return wraps(func)(compose(partial(yieldmap, self.func), func))


# TODO: docs, types
@dclass
class sendmapped:
    func: t.Callable

    def __call__(self, func):
        return wraps(func)(compose(partial(sendmap, self.func), func))


# TODO: docs, types
@dclass
class returnmapped:
    func: t.Callable

    def __call__(self, func):
        return wraps(func)(compose(partial(returnmap, self.func), func))


class query:
    """Create a query class from a generator function

    Example
    -------

    >>> @query()
    ... def post(id: int):
    ...     return json.loads((yield f'posts/{id}/'))

    Note
    ----
    The function must:

    * be a python function, bound to a module.
    * be fully annotated, without keyword-only arguments
    """
    def __call__(self,
                 func: t.Callable[..., t.Generator[T_req, T_resp, T]]) -> (
                     t.Type[Query[T, T_req, T_resp]]):
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Query, ),
            namespace={
                '__doc__':     func.__doc__,
                '__module__':  func.__module__,
                '__iter__': partialmethod(compose(
                    partial(apply, func), as_tuple)),
            }
        )
