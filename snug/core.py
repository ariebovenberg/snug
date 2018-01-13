"""the central abstractions"""
import abc
import inspect
import typing as t
from copy import copy
from functools import partial, reduce
from itertools import starmap
from operator import attrgetter, itemgetter
from types import GeneratorType

from .utils import (called_as_method, compose, nest, returnmap, sendmap,
                    yieldmap)

__all__ = [
    'Query',
    'Sender',
    'Pipe',
    'execute',
    'nested',
    'yieldmapped',
    'sendmapped',
    'returnmapped',
    'querytype',
]


T = t.TypeVar('T')
T_req = t.TypeVar('T_req')
T_resp = t.TypeVar('T_resp')
T_prepared = t.TypeVar('T_prepared')
T_parsed = t.TypeVar('T_parsed')


class Query(t.Generic[T_req, T_resp, T], t.Iterable[T_req]):
    """ABC for query-like objects.
    Any object where ``__iter__`` returns a generator implements it"""

    @abc.abstractmethod
    def __iter__(self) -> t.Generator[T_req, T_resp, T]:
        """a generator which resolves the query"""
        raise NotImplementedError()


Query.register(GeneratorType)


class Sender(t.Generic[T_req, T_resp]):
    """ABC for sender-like objects.
    Any callable with the same signature implements it"""

    def __call__(self, request: T_req) -> T_resp:
        """send a request, returning a response"""
        raise NotImplementedError()


class Pipe(t.Generic[T_req, T_prepared, T_resp, T_parsed]):
    """ABC for middleware objects.
    generator callables with the same signature implement it."""

    @abc.abstractmethod
    def __call__(self, request: T_req) -> t.Generator[T_prepared,
                                                      T_resp,
                                                      T_parsed]:
        """wrap a request and response"""
        raise NotImplementedError()

    @staticmethod
    def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
        """identity pipe, leaves requests and responses unchanged"""
        return (yield request)


class Executor(t.Generic[T_req, T_resp]):

    @abc.abstractmethod
    def __call__(self, query: Query[T_req, T_resp, T]) -> T:
        raise NotImplementedError()


def execute(query:  Query[T_req, T_resp, T],
            sender: Sender[T_req, T_resp]) -> T:
    """execute a query

    Parameters
    ----------
    query
        the query to resolve
    sender
        the sender to use
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


# TODO: docs, types
class nested:
    def __init__(self, *genfuncs):
        self._genfuncs = genfuncs

    def __call__(self, func):
        return compose(partial(reduce, nest, self._genfuncs), func)


# TODO: docs, types
class yieldmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(yieldmap, self._mapper), func)


# TODO: docs, types
class sendmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(sendmap, self._mapper), func)


# TODO: docs, types
class returnmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(returnmap, self._mapper), func)


class _WrappedQuery(Query):
    __slots__ = '_bound_args'

    def __init__(self, *args, **kwargs):
        self._bound_args = self.__signature__.bind(*args, **kwargs)
        self._bound_args.apply_defaults()

    def __iter__(self):
        return self.__wrapped__(*self._bound_args.args,
                                **self._bound_args.kwargs)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._bound_args.arguments == other._bound_args.arguments
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self == other
        return NotImplemented

    def __repr__(self):
        fields = starmap('{}={}'.format, self._bound_args.arguments.items())
        return '{}({})'.format(self.__class__.__qualname__, ', '.join(fields))

    def __hash__(self):
        return hash((self._bound_args.args,
                     tuple(self._bound_args.kwargs.items())))

    def replace(self, **kwargs):
        copied = copy(self._bound_args)
        copied.arguments.update(**kwargs)
        return self.__class__(*copied.args, **copied.kwargs)


class querytype:
    """decorate a generator function to create a reusable query class

    Example
    -------

    >>> @querytype()
    ... def post(id: int):
    ...     return json.loads((yield f'posts/{id}/'))

    is roughly equivalent to:

    >>> class post(Query):
    ...     def __init__(self, id: int):
    ...        self.id = id
    ...     def __iter__(self):
    ...         return json.loads((yield f'posts/{self.id}/))

    Note
    ----
    the decorated object must have a signature to inspect.
    """
    def __init__(self, related: bool=False):
        self._related = related

    def __call__(self, func: t.Callable) -> t.Type[Query]:
        sig = inspect.signature(func)
        origin = inspect.unwrap(func)
        cls = type(
            origin.__name__,
            (_WrappedQuery, ),
            {
                '__doc__': origin.__doc__,
                '__module__': origin.__module__,
                '__qualname__': origin.__qualname__,
                '__signature__': sig,
                '__wrapped__': staticmethod(func),
                **{
                    name: property(compose(
                        itemgetter(name),
                        attrgetter('_bound_args.arguments')))
                    for name in sig.parameters
                }
            })
        return called_as_method(cls) if self._related else cls
