"""Miscellaneous tools, boilerplate, and shortcuts"""
import typing as t
from collections import Mapping


def identity(obj):
    """identity function, returns input unmodified"""
    return obj


class compose:
    """compose a function from a chain of functions"""
    def __init__(self, *funcs: t.Callable):
        self.funcs = funcs
        self.__wrapped__ = funcs[-1] if funcs else identity

    def __call__(self, *args, **kwargs):
        if not self.funcs:
            return identity(*args, **kwargs)
        *tail, head = self.funcs
        value = head(*args, **kwargs)
        for func in reversed(tail):
            value = func(value)
        return value


class _EmptyMapping(Mapping):
    """an empty mapping to use as a default value"""
    __slots__ = ()

    def __iter__(self):
        yield from ()

    def __getitem__(self, key):
        raise KeyError(key)

    def __len__(self):
        return 0

    def __repr__(self):
        return '{}'


EMPTY_MAPPING = _EmptyMapping()
