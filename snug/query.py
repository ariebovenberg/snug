"""high-level query interface

Todos
-----
* serializing query params
* pagination
* Query as typing.Generic?
"""
import abc
import inspect
import json
import types
import typing as t
from functools import partial
from operator import methodcaller, attrgetter

import requests
from dataclasses import dataclass, field, astuple
from toolz import compose, identity, thread_last

from . import http, load
from .utils import apply

_dictfield = partial(field, default_factory=dict)

__all__ = ['Api', 'Querylike', 'Query', 'resolve', 'simple_resolve']

T = t.TypeVar('T')


@dataclass(frozen=True)
class Api:
    """an API endpoint"""
    prepare: t.Callable[[http.Request], http.Request]
    parse:   t.Callable[[http.Response], t.Any]


simple_json_api = Api(
    prepare=methodcaller('add_prefix', 'https://'),
    parse=compose(json.loads, methodcaller('decode'), attrgetter('content'))
)
"""a simple JSON api"""


class Querylike(t.Generic[T]):

    @abc.abstractproperty
    def __req__(self) -> http.Request:
        raise NotImplementedError()

    @abc.abstractproperty
    def __rtype__(self) -> t.Type[T]:
        raise NotImplementedError()


class QueryMeta(t.GenericMeta):
    """Metaclass for Query"""

    def __new__(cls, *args, rtype=object):
        created = super().__new__(cls, *args)
        created.__rtype__ = rtype
        return created

    # if the Query is nested, this is reflected in the name
    def __set_name__(self, kls, name):
        self.__name__ = f'{kls.__name__}.{self.__name__}'

    # when nested, act like a method.
    # i.e. pass the parent query instance as first argument
    def __get__(self, instance, cls):
        return self if instance is None else partial(self, instance)


class Query(Querylike[T], metaclass=QueryMeta):
    """base for all queries. Can be used as a base class,
    or initialized directly"""
    def __new__(cls, *args, **kwargs):
        if cls is Query and len(args) < 2 and not kwargs:
            # check if we're being used as a decorator
            if not args:
                return from_request_func()
            elif isinstance(args[0], type):
                return from_request_func(args[0])
            elif isinstance(args[0], types.FunctionType):
                return from_request_func()(args[0])

        return super().__new__(cls)

    def __init__(self, request, rtype=object):
        self.__req__, self.__rtype__ = request, rtype

    __req__ = NotImplemented
    __rtype__: t.Type[T] = object


@dataclass(frozen=True)
class from_request_func:
    """create a query from a function. Use as a decorator.

    The function must:
    * be a python function, bound to a module.
    * return a ``Request`` instance
    * be fully annotated, without keyword-only arguments
    """
    rtype: type = object

    def __call__(self, func: types.FunctionType):
        args, _, _, defaults, _, _, annotations = inspect.getfullargspec(func)
        return dataclass(
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
            ), frozen=True)


def resolve(query:   Querylike,
            api:     Api,
            loaders: load.Registry,
            auth:    t.Callable[[http.Request], http.Request],
            client):
    """resolve a querylike object"""
    return thread_last(
        query,
        attrgetter('__req__'),
        api.prepare,
        auth,
        (http.send, client),
        api.parse,
        loaders(query.__rtype__))


simple_resolve = partial(
    resolve,
    api=simple_json_api,
    loaders=load.simple_registry,
    auth=identity,
    client=requests.Session())
"""a basic resolver"""
