"""Tools for creating queries and query classes"""
import abc
import typing as t
from dataclasses import make_dataclass
from functools import partial, partialmethod

from .core import Query, T, T_req, T_resp
from .utils import (apply, as_tuple, compose, dclass, func_to_fields,
                    identity)

__all__ = [
    'Fixed',
    'cls_from_gen',
    'called_as_method',
]


@dclass
class Fixed(Query[T_req, T_resp, T]):
    """A static query. Useful for queries which do not take parameters.

    Parameters
    ----------
    request
        the request object
    load
        response loader

    Examples
    --------

    >>> latest_posts = query.Fixed('/posts/latest')
    >>> current_user = query.Fixed('/user/', load=load_user)
    """
    request: T_req
    load:    t.Callable[[T_resp], T] = identity

    def __iter__(self):
        return self.load((yield self.request))


@dclass
class called_as_method:
    """decorate a callable (e.g. class or function) to be called as a method.
    I.e. the parent instance is passed as the first argument"""
    target: t.Callable

    def __get__(self, instance, cls):
        return (self.target if instance is None
                else partial(self.target, instance))


class cls_from_gen:
    """Create a query class from a generator function

    Example
    -------

    >>> @query.cls_from_gen()
    ... def post(id: int):
    ...     return json.loads((yield f'posts/{id}/'))

    Note
    ----
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
                '__iter__': partialmethod(compose(
                    partial(apply, func), as_tuple)),
            }
        )
