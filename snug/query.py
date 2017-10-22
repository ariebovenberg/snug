"""high-level query interface

Todos
-----
* serializing query params
* pagination
* Query as typing.Generic?
"""
import typing as t
import types
import inspect
from functools import partial
from operator import methodcaller

from dataclasses import dataclass, field, astuple

from toolz import compose

from . import http
from .utils import apply

_dictfield = partial(field, default_factory=dict)


@dataclass(frozen=True)
class Api:
    """an API endpoint"""
    prepare: t.Callable[[http.Request], http.Request]
    parse:   t.Callable[[http.Response], t.Any]


class _Bound(type):
    """used to bind classes to the parent class in which they are declared"""

    def __set_name__(self, kls, name):
        self.__name__ = f'{kls.__name__}.{self.__name__}'

    def __get__(self, instance, cls):
        """like a method, pass the current instance as first argument"""
        return self if instance is None else partial(self, instance)


class Query(metaclass=_Bound):
    """base for all queries. Can be used as a base class,
    or initialized directly"""
    def __init__(self, request, rtype):
        self.__req__, self.__rtype__ = request, rtype

    def __init_subclass__(cls, rtype, **kwargs):
        cls.__rtype__ = rtype

    __req__ = NotImplemented
    __rtype__ = NotImplemented


@dataclass(frozen=True)
class from_func:
    """create a query from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    * have no side-effects
    """
    rtype: type

    def __call__(self, func: types.FunctionType):
        args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)
        return dataclass(frozen=True)(
            types.new_class(
                func.__name__,
                bases=(Query, ),
                kwds={'rtype': self.rtype},
                exec_body=methodcaller('update', {
                    '__annotations__': annotations,
                    '__doc__':         func.__doc__,
                    '__module__':      func.__module__,
                    '__req__':         property(compose(partial(apply, func),
                                                        astuple)),
                    **dict(zip(reversed(args), reversed(defaults or ())))
                })
            ))


def resolve(query: Query,
            api:  Api,
            load: t.Callable,
            auth: t.Callable[[http.Request], http.Request],
            client):
    """execute a query"""
    request = auth(api.prepare(query.__req__))
    return load(query.__rtype__, api.parse(http.send(client, request)))
