"""the central abstractions"""
import abc
import typing as t
from dataclasses import dataclass

__all__ = [
    'Query',
    'Sender',
    'Pipe',
    'execute',
    'nested',
]


T = t.TypeVar('T')
T_req = t.TypeVar('T_req')
T_resp = t.TypeVar('T_resp')
T_prepared = t.TypeVar('T_prepared')
T_parsed = t.TypeVar('T_parsed')


class Query(t.Generic[T, T_req, T_resp]):
    """ABC for query-like objects.
    Any object with ``__resolve__`` implements it"""

    @abc.abstractmethod
    def __resolve__(self) -> t.Generator[T_req, T_resp, T]:
        """a generator which resolves the query"""
        raise NotImplementedError()


class Sender(t.Generic[T_req, T_resp]):
    """ABC for sender-like objects.
    Any callable with the same signature implements it"""

    def __call__(self, request: T_req) -> T_resp:
        """send a request, returning a response"""
        raise NotImplementedError()


class Pipe(t.Generic[T_req, T_prepared, T_resp, T_parsed]):
    """ABC for middleware objects.
    generator functions with the same signature implement it."""

    @abc.abstractmethod
    def __call__(self, request: T_req) -> t.Generator[T_prepared,
                                                      T_resp,
                                                      T_parsed]:
        """wrap a request and response"""
        raise NotImplementedError()


def execute(sender: Sender[T_req, T_resp],
            query:  Query[T, T_req, T_resp]) -> T:
    """execute a query

    Parameters
    ----------
    sender
        the sender to use
    query
        the query to resolve
    """
    resolver = query.__resolve__()
    request = next(resolver)
    while True:
        response = sender(request)
        try:
            request = resolver.send(response)
        except StopIteration as e:
            return e.value


@dataclass
class nested:
    """a generator function created by nesting two generator functions

    Parameters
    ----------
    inner
        the inner generator function.
    pipe
        the pipe through which to pass values
    """
    inner: t.Callable[..., t.Generator[T_req, T_parsed, T]]
    pipe:  Pipe[T_req, T_prepared, T_resp, T_parsed]

    def __call__(self, *args, **kwargs) -> t.Generator[T_prepared, T_resp, T]:
        gen = self.inner(*args, **kwargs)
        request = next(gen)
        while True:
            response = yield from self.pipe(request)
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value
