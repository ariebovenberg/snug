"""Miscellaneous tools and boilerplate"""
from dataclasses import asdict


def onlyone(iterable):
    """get the only item in an iterable"""
    value, = iterable
    return value


def replace(instance, **kwargs):
    """replace values in a dataclass instance"""
    assert hasattr(instance, '__dataclass_fields__')
    return instance.__class__(**{**asdict(instance), **kwargs})
