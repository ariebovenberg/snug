"""tools for creating queries

Todo
----
* serializing query params
* pagination
"""
import abc
import typing as t
from dataclasses import make_dataclass
from functools import partial, partialmethod

from .core import Pipe, Query, T, T_req, T_resp
from .utils import (apply, as_tuple, compose, dclass, func_to_fields,
                    genresult, identity)

__all__ = [
    'Fixed',
    'Nestable',
    'Piped',
    'Base',
    'cls_from_gen',
    'cls_from_func',
]


@dclass
class Fixed(Query[T, T_req, T_resp]):
    """a static query

    Parameters
    ----------
    request
        the request
    load
        response loader
    """
    request: T_req
    load:    t.Callable[[T_resp], T] = identity

    def __resolve__(self):
        return self.load((yield self.request))


class Base(Query[T, T_req, T_resp]):
    """base class for query subclasses with useful methods to override"""

    @abc.abstractmethod
    def _request(self) -> T_req:
        """override this method to implement a requester"""
        raise NotImplementedError

    def _parse(self, response: T_resp) -> T:
        """override this method to provide custom loading of responses"""
        return response

    def __resolve__(self):
        return self._parse((yield self._request()))


@dclass
class Piped(Query[T, T_req, T_resp]):
    """a query with a pipe modifying requests/responses"""
    pipe:  Pipe
    inner: Query

    def __resolve__(self):
        resolver = self.inner.__resolve__()
        pipe = self.pipe(next(resolver))
        response = yield next(pipe)
        return resolver.send(genresult(pipe, response))


class NestableMeta(t.GenericMeta):
    """Metaclass for nested queries"""
    # when nested, act like a method.
    # i.e. pass the parent instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Nestable(metaclass=NestableMeta):
    """mixin for classes which behave like methods when called
    (i.e. pass the parent as first argument)"""


class cls_from_gen:
    """create a Query class from a generator function

    The function must:
    * be a python function, bound to a module.
    * be fully annotated, without keyword-only arguments
    """
    def __call__(self,
                 func: t.Callable[..., t.Generator[T_req, T_resp, T]]) -> (
                     t.Type[Query[T, T_req, T_resp]]):
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Query, ),
            namespace={
                '__doc__':     func.__doc__,
                '__module__':  func.__module__,
                '__resolve__': partialmethod(compose(
                    partial(apply, func), as_tuple)),
            }
        )


class cls_from_func:
    """create a query class from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * be fully annotated, without keyword-only arguments
    """
    # keyword-only arguments to prevent incorrect decorator usage
    def __init__(self, *, load: t.Callable[[T_resp], T]=identity,
                 nestable: bool=False):
        self.load = load
        self.nestable = nestable

    def __call__(self, func: t.Callable[..., T_req]) -> t.Type[
            Query[T, T_req, T_resp]]:
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Nestable, Base) if self.nestable else (Base, ),
            namespace={
                '__doc__':    func.__doc__,
                '__module__': func.__module__,
                '_request':   partialmethod(compose(
                    partial(apply, func), as_tuple)),
                '_parse':     staticmethod(self.load)
            })
