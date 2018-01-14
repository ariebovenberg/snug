"""Miscellaneous tools, boilerplate, and shortcuts"""
import inspect
import typing as t
from collections import Mapping
from datetime import datetime
from functools import partial
from types import MethodType

T = t.TypeVar('T')


class CallableAsMethod:
    """mixin for callables to support method-like calling

    See also
    --------
    `https://docs.python.org/3/howto/descriptor.html#functions-and-methods`
    """
    def __get__(self, obj, objtype=None):
        return self if obj is None else MethodType(self, obj)


def notnone(obj):
    """return whether an object is not None"""
    return obj is not None


class NO_DEFAULT:
    """sentinel for no default"""


class lookup_defaults:
    """wrap a lookup function with a default if lookup fails"""
    def __init__(self, lookup: t.Callable[[t.Any], T], default: T):
        self.lookup, self.default = lookup, default

    def __call__(self, obj):
        try:
            return self.lookup(obj)
        except LookupError:
            return self.default


def parse_iso8601(dtstring: str) -> datetime:
    """naive parser for ISO8061 datetime strings,

    Parameters
    ----------
    dtstring
        the datetime as string in one of two formats:

        * ``2017-11-20T07:16:29+0000``
        * ``2017-11-20T07:16:29Z``

    """
    return datetime.strptime(
        dtstring,
        '%Y-%m-%dT%H:%M:%SZ' if len(dtstring) == 20 else '%Y-%m-%dT%H:%M:%S%z')


# TODO: type annotations
def genresult(gen, value):
    """send an item into a generator expecting a final return value"""
    try:
        gen.send(value)
    except StopIteration as e:
        return e.value
    else:
        raise TypeError('generator did not return as expected')


def identity(obj):
    """identity function, returns input unmodified"""
    return obj


class flip:
    """create a function with flipped arguments

    Parameters
    ----------
    func
        the function to flip
    """
    def __init__(self, func: t.Callable):
        self.func = func

    def __call__(self, a, b):
        return self.func(b, a)

    def __eq__(self, other):
        if isinstance(other, flip):
            return self.func == other.func
        return NotImplemented

    def __hash__(self):
        return hash(self.func)

    def __ne__(self, other):
        if isinstance(other, flip):
            return not self == other
        return NotImplemented

    def __repr__(self):
        return 'flipped({.func})'.format(self)


class compose(CallableAsMethod):
    """compose a function from a chain of functions

    Parameters
    ----------
    *funcs
        callables to compose

    Note
    ----
    * if given no functions, acts as :func:`identity`
    * constructs an inspectable :class:`~inspect.Signature` if possible
    """
    def __init__(self, *funcs: t.Callable):
        self.funcs = funcs
        # determine the composed signature, if underlying callables
        # support it.
        if funcs:
            self.__wrapped__ = funcs[-1]
            try:
                return_sig = inspect.signature(funcs[0])
            except ValueError:
                return_annotation = inspect.Signature.empty
            else:
                return_annotation = return_sig.return_annotation

            try:
                self.__signature__ = inspect.signature(
                    funcs[-1]).replace(return_annotation=return_annotation)
            except ValueError:  # the callable does not support signature
                pass
        else:
            self.__wrapped__ = identity

    def __hash__(self):
        return hash(self.funcs)

    def __eq__(self, other):
        if isinstance(other, compose):
            return self.funcs == other.funcs
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, compose):
            return self.funcs != other.funcs
        return NotImplemented

    def __call__(self, *args, **kwargs):
        if not self.funcs:
            return identity(*args, **kwargs)
        *tail, head = self.funcs
        value = head(*args, **kwargs)
        for func in reversed(tail):
            value = func(value)
        return value


class called_as_method:
    """decorate a callable (e.g. class or function) to be called as a method.
    I.e. the parent instance is passed as the first argument"""
    def __init__(self, func: t.Callable):
        self.func = func

    def __get__(self, instance, cls):
        return (self.func if instance is None
                else partial(self.func, instance))


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


# TODO inner type annotations
def valmap(func: t.Callable, mapping: t.Mapping) -> t.Mapping:
    """map() for values of a mapping"""
    return {k: func(v) for k, v in mapping.items()}


# TODO inner type annotations
def valfilter(predicate: t.Callable, mapping: t.Mapping) -> t.Mapping:
    """filter() for values of a mapping"""
    return {k: v for k, v in mapping.items() if predicate(v)}


def push(value, *funcs):
    """pipe a value through a sequence of functions"""
    for func in funcs:
        value = func(value)
    return value


class _EmptyMapping(Mapping):
    """an empty mapping to use as a default value"""
    def __iter__(self):
        yield from ()

    def __getitem__(self, key):
        raise KeyError(key)

    def __len__(self):
        return 0

    def __repr__(self):
        return '{}'


EMPTY_MAPPING = _EmptyMapping()
