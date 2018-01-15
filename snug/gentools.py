import inspect
import typing as t
from functools import partial, reduce

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
]


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
