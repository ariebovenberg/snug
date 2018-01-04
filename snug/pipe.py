"""middleware abstractions"""
import typing as t
from dataclasses import dataclass
from functools import partial, reduce

from .core import Pipe, T_req, T_resp
from .utils import nest

_dclass = partial(dataclass, frozen=True)


def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
    """identity pipe, leaves requests and responses unchanged"""
    return (yield request)


@dataclass(init=False)
class Chain(Pipe):
    """a chained pipe, applying pipes in order"""
    stages: t.Tuple[Pipe, ...]

    def __init__(self, *stages):
        self.stages = stages

    def __call__(self, request) -> t.Generator:
        return (yield from reduce(nest, self.stages, identity(request)))

    def __or__(self, other: Pipe):
        return Chain(*(self.stages + (other, )))
