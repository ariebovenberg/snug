"""the central abstractions"""
import abc
import inspect
import typing as t
from functools import partial, wraps
from types import GeneratorType
from operator import itemgetter, attrgetter

from .utils import compose, nest, yieldmap, sendmap, returnmap

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
    def __init__(self, thru):
        self.thru = thru

    def __call__(self, func):
        return wraps(func)(compose(partial(nest, pipe=self.thru), func))


# TODO: docs, types
class yieldmapped:
    def __init__(self, func):
        self.func = func

    def __call__(self, func):
        return wraps(func)(compose(partial(yieldmap, self.func), func))


# TODO: docs, types
class sendmapped:
    def __init__(self, func):
        self.func = func

    def __call__(self, func):
        return wraps(func)(compose(partial(sendmap, self.func), func))


# TODO: docs, types
class returnmapped:
    def __init__(self, func):
        self.func = func

    def __call__(self, func):
        return wraps(func)(compose(partial(returnmap, self.func), func))


class _WrappedQuery(Query):
    __slots__ = 'bound_args'

    def __init__(self, *args, **kwargs):
        self.bound_args = self.__signature__.bind(*args, **kwargs)
        self.bound_args.apply_defaults()

    def __iter__(self):
        return self.__wrapped__(*self.bound_args.args,
                                **self.bound_args.kwargs)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.bound_args.arguments == other.bound_args.arguments
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self == other
        return NotImplemented

    def __repr__(self):
        fields = (f'{n}={v}' for n, v in self.bound_args.arguments.items())
        return f'{self.__class__.__qualname__}({", ".join(fields)})'

    def __hash__(self):
        return hash((self.bound_args.args,
                     tuple(self.bound_args.kwargs.items())))


class querytype:
    """decorate a query function to create a reusable query class

    Example
    -------

    >>> @querytype()
    ... def post(id: int):
    ...     return json.loads((yield f'posts/{id}/'))

    Note
    ----
    the callable must have a signature.
    """
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
                    name: property(compose(itemgetter(name),
                                           attrgetter('bound_args.arguments')))
                    for name in sig.parameters
                }
            })
        return cls
