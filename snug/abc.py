"""the central abstractions"""
import abc
import typing as t

from .utils import genresult

__all__ = [
    'Query',
    'Sender',
    'resolve',
]


T = t.TypeVar('T')
T_req = t.TypeVar('T_req')
T_resp = t.TypeVar('T_resp')


class Query(t.Generic[T, T_req, T_resp]):
    """ABC for query-like objects.
    Any object with ``__resolve__`` implements it"""

    @abc.abstractmethod
    def __resolve__(self) -> t.Generator[T_req, T_resp, T]:
        raise NotImplementedError()


class Sender(t.Generic[T_req, T_resp]):
    """ABC for sender-like objects.
    Any callable with the same signature implements it"""

    def __call__(self, request: T_req) -> T_resp:
        raise NotImplementedError()


def resolve(sender: Sender[T_req, T_resp],
            query: Query[T, T_req, T_resp]) -> T:
    """resolve a query

    Parameters
    ----------
    resolver
        the resolver to use
    query
        the query to resolve
    """
    res = query.__resolve__()
    response = sender(next(res))
    return genresult(res, response)
