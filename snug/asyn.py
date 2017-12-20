"""functionality for asynchronous behavior"""
import typing as t

from .abc import Query, T, T_req, T_resp
from .pipe import Pipe, T_parsed, T_prepared
from .utils import dclass, genresult


class Sender(t.Generic[T_req, T_resp]):
    """ABC for asynchronous resolver-like objects.
    Any callable with the same signature implements it"""

    def __call__(self, request: T_req) -> t.Awaitable[T_resp]:
        raise NotImplementedError()


async def resolve(sender: Sender[T_req, T_resp],
                  query: Query[T, T_req, T_resp]) -> t.Awaitable[T]:
    """resolve a query asynchronously

    Parameters
    ----------
    resolver
        the resolver to use
    query
        the query to resolve
    """
    res = query.__resolve__()
    response = await sender(next(res))
    return genresult(res, response)


@dclass
class PipedSender(Sender[T_req, T_parsed]):
    """an async sender wrapped with a pipe"""
    inner: Sender[T_prepared, T_resp]
    pipe:  Pipe[T_req, T_prepared, T_resp, T_parsed]

    async def __call__(self, request):
        wrap = self.pipe(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)
