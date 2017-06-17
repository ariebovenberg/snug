"""classes and utilities for dealing with JSON API data"""
from functools import reduce
import collections.abc

from . import core


def _getitem(obj, key):
    return obj[key]


class Resource(core.Resource, abstract=True):

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.api_obj[key]
        elif isinstance(key, collections.abc.Iterable):
            return reduce(_getitem, key, self.api_obj)
        else:
            raise TypeError(type(key))
