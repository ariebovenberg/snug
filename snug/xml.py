"""shortcuts for working with XML data"""
import typing as t
from functools import partial
from operator import (methodcaller, attrgetter as _attrgetter,
                      itemgetter as _itemgetter)
from xml.etree.ElementTree import Element

from toolz import compose, identity

from .utils import NO_DEFAULT, lookup_defaults

T = t.TypeVar('T')


def elemgetter(path: str) -> t.Callable[[Element], Element]:
    """shortcut making an XML element getter"""
    return compose(
        partial(_raise_if_none, exc=LookupError(path)),
        methodcaller('find', path)
    )


# type: str -> Callable[[Element], List[Element]]
elemsgetter = partial(methodcaller, 'findall')


def textsgetter(path: str, *, strip: bool=False) -> t.Callable[[Element],
                                                               t.List[str]]:
    return compose(list,
                   partial(map, str.strip) if strip else identity,
                   partial(map, _attrgetter('text')),
                   methodcaller('findall', path))


def textgetter(path: str, *,
               default: T=NO_DEFAULT,
               strip: bool=False) -> t.Callable[[Element], t.Union[str, T]]:
    """shortcut for making an XML element text getter"""
    find = compose(
        str.strip if strip else identity,
        partial(_raise_if_none, exc=LookupError(path)),
        methodcaller('findtext', path)
    )
    return (find if default is NO_DEFAULT else lookup_defaults(find, default))


def attribgetter(path: str,
                 attname: str, *,
                 default: T=NO_DEFAULT) -> t.Callable[[Element],
                                                      t.Union[str, T]]:
    find = compose(
        _itemgetter(attname),
        _attrgetter('attrib'),
        partial(_raise_if_none, exc=LookupError(path)),
        methodcaller('find', path)
    )
    return (find if default is NO_DEFAULT else lookup_defaults(find, default))


def _raise_if_none(value, exc):
    if value is None:
        raise exc
    return value
