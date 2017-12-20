"""middleware abstractions"""
import abc
import json
import typing as t
from dataclasses import dataclass, replace
from functools import partial

from .abc import T_req, T_resp
from . import http
from .utils import genresult, push, JSONType

dclass = partial(dataclass, frozen=True)

T_prepared = t.TypeVar('T_prepared')
T_parsed = t.TypeVar('T_parsed')


class Pipe(t.Generic[T_req, T_prepared, T_resp, T_parsed]):
    """ABC for middleware objects.
    generator functions with the same signature implement it."""

    @abc.abstractmethod
    def __call__(self, request: T_req) -> t.Generator[T_prepared,
                                                      T_resp,
                                                      T_parsed]:
        raise NotImplementedError()


def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
    """identity pipe, leaves requests and responses unchanged"""
    return (yield request)


@dclass
class Sender(http.Sender[T_req, T_parsed]):
    """a wrapped sender"""
    inner:   http.Sender[T_prepared, T_resp]
    pipe: Pipe[T_req, T_prepared, T_resp, T_parsed]

    def __call__(self, request):
        wrap = self.pipe(request)
        response = self.inner(next(wrap))
        return genresult(wrap, response)


@dclass
class AsyncSender(http.AsyncSender[T_req, T_parsed]):
    """a wrapped asynchronous sender"""
    inner: http.AsyncSender[T_prepared, T_resp]
    pipe:  Pipe[T_req, T_prepared, T_resp, T_parsed]

    async def __call__(self, request):
        wrap = self.pipe(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)


class Base(Pipe[T_req, T_prepared, T_resp, T_parsed]):
    """a simple base class to inherit from"""

    def _prepare(self, request: T_req) -> T_prepared:
        """override this to customize request preparing"""
        return request

    def _parse(self, response: T_resp) -> T_parsed:
        """override this to customize response parsing"""
        return response

    def __call__(self, request):
        response = yield self._prepare(request)
        return self._parse(response)


@dclass
class Preparer(Pipe[T_req, T_prepared, T_resp, T_resp]):
    """A pipe which only does preparing of a request"""
    prepare: t.Callable[[T_req], T_prepared]

    def __call__(self, request):
        return (yield self.prepare(request))


@dclass
class Parser(Pipe[T_req, T_req, T_resp, T_parsed]):
    """a pipe which only does parsing of the result"""
    parse: t.Callable[[T_resp], T_parsed]

    def __call__(self, request):
        return self.parse((yield request))


@dataclass(init=False)
class Chain(Pipe):
    """a chained pipe, applying pipes in order"""
    stages: t.Tuple[Pipe, ...]

    def __init__(self, *stages):
        self.stages = stages

    def __call__(self, request):
        wraps = []
        for pipe in self.stages:
            wrap = pipe(request)
            wraps.append(wrap)
            request = next(wrap)

        response = yield request

        return push(
            response,
            *(partial(genresult, p) for p in reversed(wraps)))

    def __or__(self, other: Pipe):
        return Chain(*(self.stages + (other, )))


def jsondata(request: http.Request[t.Optional[bytes]]) -> t.Generator[
        http.Request[JSONType], http.Response[t.Optional[bytes]], JSONType]:
    """a simple pipe for requests with JSON content"""
    prepared = (replace(request, data=json.dumps(request.data).encode('ascii'))
                if request.data else request)
    response = yield prepared
    return json.loads(response.data) if response.data else None
