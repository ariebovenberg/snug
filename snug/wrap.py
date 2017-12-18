"""middleware abstractions"""
import abc
import json
import typing as t
from dataclasses import dataclass, replace
from functools import partial

from . import http
from .utils import genresult, pipe, JSONType

dclass = partial(dataclass, frozen=True)


T_req = t.TypeVar('T_req')
T_prepared = t.TypeVar('T_req_out')
T_resp = t.TypeVar('T_resp')
T_parsed = t.TypeVar('T_resp_out')


class Wrapper(t.Generic[T_req, T_prepared, T_resp, T_parsed]):
    """ABC for middleware"""

    @abc.abstractmethod
    def __call__(self, request: T_req) -> t.Generator[T_prepared,
                                                      T_resp,
                                                      T_parsed]:
        raise NotImplementedError()


def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
    """identity wrapper, leaves requests and responses unchanged"""
    return (yield request)


@dclass
class Sender(http.Sender[T_req, T_parsed]):
    """a wrapped sender"""
    inner:   http.Sender[T_prepared, T_resp]
    wrapper: Wrapper[T_req, T_prepared, T_resp, T_parsed]

    def __call__(self, request):
        wrap = self.wrapper(request)
        response = self.inner(next(wrap))
        return genresult(wrap, response)


@dclass
class AsyncSender(http.AsyncSender[T_req, T_parsed]):
    """a wrapped asynchronous sender"""
    inner:   http.AsyncSender[T_prepared, T_resp]
    wrapper: Wrapper[T_req, T_prepared, T_resp, T_parsed]

    async def __call__(self, request):
        wrap = self.wrapper(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)


class Base(Wrapper[T_req, T_prepared, T_resp, T_parsed]):
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
class Preparer(Wrapper[T_req, T_prepared, T_resp, T_resp]):
    """A wrapper which only does preparing of a request"""
    prepare: t.Callable[[T_req], T_prepared]

    def __call__(self, request):
        return (yield self.prepare(request))


@dclass
class Parser(Wrapper[T_req, T_req, T_resp, T_parsed]):
    """a wrapper which only does parsing of the result"""
    parse: t.Callable[[T_resp], T_parsed]

    def __call__(self, request):
        return self.parse((yield request))


@dclass
class Chain(Wrapper):
    """a chained wrapper, applying wrappers in order"""
    wrappers: t.Tuple[Wrapper, ...] = ()

    def __call__(self, request):
        wraps = []
        for wrapper in self.wrappers:
            wrap = wrapper(request)
            wraps.append(wrap)
            request = next(wrap)

        response = yield request

        return pipe(
            response,
            *(partial(genresult, wrapper) for wrapper in reversed(wraps)))

    def __or__(self, other: Wrapper):
        return Chain(self.wrappers + (other, ))


def jsondata(request: http.Request[t.Optional[bytes]]) -> t.Generator[
        http.Request[JSONType], http.Response[t.Optional[bytes]], JSONType]:
    """a simple wrapper for requests with JSON content"""
    prepared = (replace(request, data=json.dumps(request.data).encode('ascii'))
                if request.data else request)
    response = yield prepared
    return json.loads(response.data) if response.data else None
