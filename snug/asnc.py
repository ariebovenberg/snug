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


async def execute(query:  Query[T_req, T_resp, T],
                  sender: Sender[T_req, T_resp]) -> T:
    """execute a query asynchronously

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
        response = await sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value
