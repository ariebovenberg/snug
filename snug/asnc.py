"""functionality for asynchronous behavior"""
import abc
import typing as t

from .core import Query, T, T_req, T_resp


class Executor(t.Generic[T_req, T_resp]):

    @abc.abstractmethod
    async def __call__(self, query: Query[T_req, T_resp, T]) -> T:
        raise NotImplementedError()


class Sender(t.Generic[T_req, T_resp]):
    """ABC for asynchronous resolver-like objects.
    Any callable with the same signature implements it"""
    async def __call__(self, request: T_req) -> T_resp:
        raise NotImplementedError()


async def exec(sender: Sender[T_req, T_resp],
               query:  Query[T_req, T_resp, T]) -> T:
    """execute a query asynchronously

    Parameters
    ----------
    sender
        the sender to use
    query
        the query to resolve
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = await sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value
