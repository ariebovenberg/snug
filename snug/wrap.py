"""middleware abstractions"""
import abc
import json
import typing as t
from dataclasses import dataclass, replace
from functools import partial

from . import http
from .utils import genresult, pipe

dclass = partial(dataclass, frozen=True)


class Wrapper(abc.ABC):
    """ABC for middleware"""

    @abc.abstractmethod
    def __call__(self, request) -> t.Generator:
        raise NotImplementedError()


@dclass
class Sender(http.Sender):
    """a wrapped sender"""
    inner:   http.Sender
    wrapper: Wrapper

    def __call__(self, request):
        wrap = self.wrapper(request)
        response = self.inner(next(wrap))
        return genresult(wrap, response)


@dclass
class AsyncSender(http.AsyncSender):
    """a wrapped asynchronous sender"""
    inner:   http.AsyncSender
    wrapper: Wrapper

    async def __call__(self, request):
        wrap = self.wrapper(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)


class Base(Wrapper):
    """a simple base class to inherit from"""

    def _prepare(self, request):
        return request

    def _parse(self, response):
        return response

    def __call__(self, request):
        response = yield self._prepare(request)
        return self._parse(response)


@dclass
class Preparer(Wrapper):
    """A wrapper which only does preparing of a request"""
    prepare: t.Callable[[http.Request], http.Request]

    def __call__(self, request):
        return (yield self.prepare(request))


@dclass
class Chain(Wrapper):
    """a chained wrapper, applying wrappers in order"""
    wrappers: t.Tuple[Wrapper] = ()

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


def jsondata(request):
    """a simple wrapper for requests with JSON content"""
    prepared = (replace(request, data=json.dumps(request.data).encode('ascii'))
                if request.data else request)
    response = yield prepared
    return json.loads(response.data) if response.data else None
