"""Miscellaneous tools and boilerplate"""
from operator import truth, itemgetter

from dataclasses import asdict
from toolz import compose


def onlyone(iterable):
    """get the only item in an iterable"""
    value, = iterable
    return value


def replace(instance, **kwargs):
    """replace values in a dataclass instance"""
    assert hasattr(instance, '__dataclass_fields__')
    return instance.__class__(**{**asdict(instance), **kwargs})


_truthy_item = compose(truth, itemgetter(1))


def filteritems(items):
    return filter(_truthy_item, items)
