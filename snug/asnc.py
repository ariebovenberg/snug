"""functionality for asynchronous behavior"""
import typing as t

from .core import Pipe, Query, T, T_parsed, T_prepared, T_req, T_resp
from .utils import dclass, genresult


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


@dclass
class PipedSender(Sender[T_req, T_parsed]):
    """an async sender wrapped with a pipe"""
    pipe:  Pipe[T_req, T_prepared, T_resp, T_parsed]
    inner: Sender[T_prepared, T_resp]

    async def __call__(self, request):
        wrap = self.pipe(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)
