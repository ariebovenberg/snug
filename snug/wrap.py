"""middleware abstractions"""
import abc
import typing as t
from functools import partial

from dataclasses import dataclass
from toolz import thread_last

from .utils import genresult
from . import http

dclass = partial(dataclass, frozen=True)


class Wrapper(abc.ABC):
    """ABC for middleware"""

    @abc.abstractmethod
    def __wrap__(self, request) -> t.Generator:
        raise NotImplementedError()


@dclass
class Sender(http.Sender):
    """a wrapped sender"""
    inner:   http.Sender
    wrapper: Wrapper

    def __call__(self, request):
        wrap = self.wrapper.__wrap__(request)
        response = self.inner(next(wrap))
        return genresult(wrap, response)


@dclass
class AsyncSender(http.AsyncSender):
    """a wrapped asynchronous sender"""
    inner:   http.AsyncSender
    wrapper: Wrapper

    async def __call__(self, request):
        wrap = self.wrapper.__wrap__(request)
        response = await self.inner(next(wrap))
        return genresult(wrap, response)


class Base(Wrapper):
    """a simple base class to inherit from"""

    def prepare(self, request):
        return request

    def parse(self, response):
        return response

    def __wrap__(self, request):
        response = yield self.prepare(request)
        return self.parse(response)


@dclass
class Static(Wrapper):
    """a static wrapper from a generator"""
    gen: t.Callable[[t.Any], t.Generator]

    def __wrap__(self, request):
        return self.gen(request)


@dclass
class Chain(Wrapper):
    """a chained wrapper, applying wrappers in order"""
    wrappers: t.Sequence[Wrapper] = ()

    def __wrap__(self, request):
        wraps = []
        for wrapper in self.wrappers:
            wrap = wrapper.__wrap__(request)
            wraps.append(wrap)
            request = next(wrap)

        response = yield request

        return thread_last(
            response,
            *((genresult, wrapper) for wrapper in wraps))

    def __or__(self, other: Wrapper):
        return Chain(list(self.wrappers) + [other])
