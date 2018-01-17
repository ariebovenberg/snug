import abc
import inspect
import typing as t
from copy import copy
from functools import partial, reduce
from itertools import starmap
from operator import attrgetter, itemgetter

from .utils import compose

__all__ = [
    'nest',
    'yieldmap',
    'sendmap',
    'returnmap',
    'nested',
    'yieldmapped',
    'sendmapped',
    'returnmapped',
    'Generable',
    'reusable',
    'ReusableGenerator',
]


T_yield = t.TypeVar('T_yield')
T_send = t.TypeVar('T_send')
T_return = t.TypeVar('T_return')


class Generable(t.Generic[T_yield, T_send, T_return], t.Iterable[T_yield]):
    """ABC for query-like objects.
    Any object where ``__iter__`` returns a generator implements it"""

    @abc.abstractmethod
    def __iter__(self) -> t.Generator[T_yield, T_send, T_return]:
        """a generator which resolves the query"""
        raise NotImplementedError()


class ReusableGenerator(Generable):
    """abstract base for reusable generator functions

    Warning
    -------
    do not subclass directly.
    Create a subclass with the :func:`reusable` decorator.
    """
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
        fields = starmap('{}={!r}'.format, self._bound_args.arguments.items())
        return '{}({})'.format(self.__class__.__qualname__, ', '.join(fields))

    def __hash__(self):
        return hash((self._bound_args.args,
                     tuple(self._bound_args.kwargs.items())))

    def replace(self, **kwargs):
        copied = copy(self._bound_args)
        copied.arguments.update(**kwargs)
        return self.__class__(*copied.args, **copied.kwargs)


def reusable(func: t.Callable) -> t.Type[Generable]:
    sig = inspect.signature(func)
    origin = inspect.unwrap(func)
    return type(
        origin.__name__,
        (ReusableGenerator, ),
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


# TODO: type annotations
def genresult(gen, value):
    """send an item into a generator expecting a final return value"""
    try:
        gen.send(value)
    except StopIteration as e:
        return e.value
    else:
        raise TypeError('generator did not return as expected')


# TODO: types, docstring
def yieldmap(func, gen) -> t.Generator:
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send((yield func(item)))


# TODO: type annotations, docstring
def sendmap(func, gen) -> t.Generator:
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send(func((yield item)))


# TODO: type annotations, docstring
def nest(gen, pipe):
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        sent = yield from pipe(item)
        item = gen.send(sent)


# TODO: type annotations, docstring
def returnmap(func, gen):
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    return func((yield from gen))


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


# TODO: type annotations
class oneyield:
    """decorate a function to turn it into a basic generator"""
    def __init__(self, func: t.Callable):
        self.__wrapped__ = func

    def __call__(self, *args, **kwargs):
        return (yield self.__wrapped__(*args, **kwargs))
