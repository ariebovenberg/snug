"""middleware abstractions"""
import typing as t
from dataclasses import dataclass
from functools import partial

from .core import Pipe, T_parsed, T_prepared, T_req, T_resp
from .utils import genresult, push

_dclass = partial(dataclass, frozen=True)


def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
    """identity pipe, leaves requests and responses unchanged"""
    return (yield request)


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


@_dclass
class Preparer(Pipe[T_req, T_prepared, T_resp, T_resp]):
    """A pipe which only does preparing of a request"""
    prepare: t.Callable[[T_req], T_prepared]

    def __call__(self, request):
        return (yield self.prepare(request))


@_dclass
class Parser(Pipe[T_req, T_req, T_resp, T_parsed]):
    """a pipe which only does parsing of the response"""
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
