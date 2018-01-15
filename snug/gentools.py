import inspect
import typing as t


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


# TODO: type annotations
class oneyield:
    """decorate a function to turn it into a basic generator"""
    def __init__(self, func: t.Callable):
        self.__wrapped__ = func

    def __call__(self, *args, **kwargs):
        return (yield self.__wrapped__(*args, **kwargs))
