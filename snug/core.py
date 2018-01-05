"""the central abstractions"""
import abc
import typing as t
from functools import partial
from types import GeneratorType

from .utils import compose, nest, dclass, yieldmap, sendmap, returnmap

__all__ = [
    'Query',
    'Sender',
    'Pipe',
    'exec',
    'nested',
    'yieldmapped',
    'sendmapped',
    'returnmapped',
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


class Executor(t.Generic[T_req, T_resp]):

    @abc.abstractmethod
    def __call__(self, query: Query[T_req, T_resp, T]) -> T:
        raise NotImplementedError()


def exec(query:  Query[T_req, T_resp, T],
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
        return compose(partial(nest, pipe=self.thru), func)


# TODO: docs, types
@dclass
class yieldmapped:
    func: t.Callable

    def __call__(self, func):
        return compose(partial(yieldmap, self.func), func)


# TODO: docs, types
@dclass
class sendmapped:
    func: t.Callable

    def __call__(self, func):
        return compose(partial(sendmap, self.func), func)


# TODO: docs, types
@dclass
class returnmapped:
    func: t.Callable

    def __call__(self, func):
        return compose(partial(returnmap, self.func), func)
