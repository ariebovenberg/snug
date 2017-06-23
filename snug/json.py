"""Classes and utilities for dealing with JSON API data"""
import collections.abc
from functools import reduce
from typing import Union, Iterable

from . import core


def _getitem(obj, key):
    return obj[key]


class Resource(core.Resource, abstract=True):
    """A resource for use in JSON-based API's"""

    def __getitem__(self, key: Union[str, Iterable]):
        """get a value from the underlying API object.

        Parameters
        ----------
        key
            the key to retrieve. May be a string, or a sequence of strings
            to retrieve nested values.
        """
        if isinstance(key, str):
            return self.api_obj[key]
        elif isinstance(key, collections.abc.Iterable):
            return reduce(_getitem, key, self.api_obj)
        else:
            raise TypeError(type(key))
