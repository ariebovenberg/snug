"""Miscellaneous tools and shortcuts"""
from dataclasses import asdict


def onlyone(iterable):
    """get the only item in an iterable"""
    value, = iterable
    return value


def replace(instance, **kwargs):
    """replace values in a dataclass instance"""
    return instance.__class__(**{**asdict(instance), **kwargs})


def apply(func, args=(), kwargs=None):
    """apply args and kwargs to a function"""
    return func(*args, **kwargs or {})


def notnone(obj):
    """return whether an object is not None"""
    return obj is not None


class StrRepr():
    """mixin which includes a __repr__ based on __str__"""

    def __str__(self):
        return '{0.__class__.__name__} object'.format(self)

    def __repr__(self):
        return '<{0.__class__.__name__}: {0}>'.format(self)
