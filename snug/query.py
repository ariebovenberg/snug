"""Tools for creating queries and query classes"""
import typing as t
from dataclasses import make_dataclass
from functools import partial, partialmethod

from .core import Query, T, T_req, T_resp
from .utils import apply, as_tuple, compose, func_to_fields

__all__ = [
    'cls_from_gen',
]


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
