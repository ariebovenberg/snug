import collections
import typing as t
from operator import attrgetter
from functools import singledispatch

import lxml.etree
from toolz import partial, curry

from .utils import onlyone


LoadRegistry = t.Mapping[type, t.Callable]
NoneType = type(None)


def _is_optional_type(cls):
    try:
        return (cls.__origin__ is t.Union
                and len(cls.__args__) == 2
                and cls.__args__[1] is NoneType)
    except AttributeError:
        return False


def _is_collection_type(cls):
    try:
        return issubclass(cls.__origin__, collections.abc.Collection)
    except AttributeError:
        return False


def _deconstruct_type(typ):
    """for a given type, return a tuple (type, multiple, optional)"""
    optional = _is_optional_type(typ)
    if optional:
        typ = typ.__args__[0]

    multiple = _is_collection_type(typ)
    if multiple:
        typ, = typ.__args__

    return (typ, multiple, optional)


def _load_value(value, loader, multiple, optional):
    if value is None and optional:
        return None
    if multiple:
        return list(map(loader, value))
    return loader(value)


def registered_dataclass_loader(dclass: type,
                                sourcemap: t.Mapping[str, str],
                                loaders: LoadRegistry):
    """generate and register a function to load a dataclass

    Parameters
    ----------
    dclass: type
        the dataclass
    sourcemap: Mapping[str, str]
        maps fieldnames to their source
    loaders: LoadRegistry
        the registry of type loaders

    Returns
    -------
    Callable
        a loader function, returning an object of type ``dclass``

    """
    loader = loaders[dclass] = _loader_for_dataclass(
        dclass, sourcemap, loaders)
    return loader


def _loader_for_dataclass(dclass, sourcemap, loaders):
    fields = dclass.__dataclass_fields__
    sources = map(sourcemap.__getitem__, fields)
    types = list(map(_deconstruct_type,
                     map(attrgetter('type'), fields.values())))

    itemgetters = [
        partial(getitem, key=source, multiple=multiple, optional=optional)
        for source, (_, multiple, optional) in zip(sources, types)
    ]

    def loader(obj):
        raw_values = (getter(obj) for getter in itemgetters)
        values = (_load_value(val, loaders[typ], multiple, optional)
                  for val, (typ, multiple, optional) in zip(raw_values, types))
        return dclass(*values)

    return loader


def list_(typeargs, value, loaders):
    """loader for the List generic type"""
    subtype, = typeargs
    return list(map(load(subtype, loaders=loaders), value))


def optional(typeargs, value, loaders):
    """loader for the Union[..., None] generic type"""
    subtype, nonetype = typeargs
    assert nonetype is NoneType, 'type is not an Optional'
    return value if value is None else load(subtype, value, loaders=loaders)


@curry
def load(cls: type, value, loaders: LoadRegistry):
    """load an object with given type. Curried function.

    Parameters
    ----------
    cls: type
        the result type
    value: Any
        the value to be loaded
    loaders: LoadRegistry
        registry of type loaders

    Returns
    -------
    cls
    """
    loader = (partial(loaders[cls.__origin__], cls.__args__,
                      loaders=loaders)
              if hasattr(cls, '__origin__')
              else loaders[cls])
    return loader(value)


@singledispatch
def getitem(obj, key: str, multiple: bool, optional: bool):
    """get a value from an API object"""
    raise TypeError(obj)


@getitem.register(collections.Mapping)
def _mapping_getitem(obj, key, multiple, optional):
    return obj.get(key) if optional else obj[key]


@getitem.register(lxml.etree._Element)
def _lxml_getitem(obj, key, multiple, optional):
    values = obj.xpath(key)
    if not values and not multiple:
        if optional:
            return None
        else:
            raise LookupError(key)
    return values if multiple else onlyone(values)
