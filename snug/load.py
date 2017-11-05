"""Tools for deserialization"""
import abc
import collections
import typing as t
from datetime import datetime
from functools import singledispatch, partial
from itertools import starmap
from operator import attrgetter

import dateutil.parser
import lxml.etree
from dataclasses import dataclass, field
from toolz import valmap, compose, identity

from .utils import onlyone

__all__ = ['Registry', 'Loader', 'CombinableRegistry', 'MultiRegistry',
           'PrimitiveRegistry', 'GenericRegistry', 'AutoDataclassRegistry',
           'create_dataclass_loader', 'list_loader', 'set_loader',
           'get_optional_loader', 'simple_registry', 'getitem']

T = t.TypeVar('T')
NoneType = type(None)
_dictfield = partial(field, default_factory=dict)


Loader = t.Callable[[t.Any], T]


class Loader(t.Generic[T]):
    """Interface for loaders (deserializers).
    Any callable with the signature ``Any -> T`` implements ``Loader[T]``
    """
    def __call__(self, value: t.Any) -> T:
        """loads an object of a particular type from any data"""
        raise NotImplementedError()


class Registry(abc.ABC):
    """Interface for a loader registry.
    Any callable with signature ``Type[T] -> Loader[T]`` implements it.
    """

    @abc.abstractmethod
    def __call__(self, cls: t.Type[T]) -> Loader[T]:
        raise NotImplementedError()


class CombinableRegistry(Registry):
    """base class for registries which may be combined

    any callable implemeting the signature
    ``(t.Type[T], Registry) -> Loader[T]``
    is combinable

    also provides ``__or__`` as a mixin method
    """

    @abc.abstractmethod
    def __call__(self, cls: t.Type[T], main: Registry) -> Loader[T]:
        raise NotImplementedError()

    def __or__(self, other: 'CombinableRegistry') -> 'MultiRegistry':
        return MultiRegistry([self, other])


@dataclass(frozen=True, hash=False)
class MultiRegistry(CombinableRegistry):
    children: t.List[CombinableRegistry]

    def __call__(self, cls, main=None):
        exc = None
        for registry in self.children:
            exc = None
            try:
                return registry(cls, main=main or self)
            except UnsupportedType as excep:
                exc = excep
        raise exc

    def __or__(self, other: CombinableRegistry) -> 'MultiRegistry':
        return MultiRegistry([*self.children, other])


@dataclass(frozen=True, hash=False)
class PrimitiveRegistry(CombinableRegistry):
    """a registry of primitive (i.e. non-nested) loaders"""
    registry: t.Mapping[t.Type[T], t.Callable[[t.Any], T]] = _dictfield()

    def __call__(self, cls, main=None):
        try:
            return self.registry[cls]
        except KeyError:
            raise UnsupportedType(cls)


@dataclass(frozen=True, hash=False)
class GenericRegistry(CombinableRegistry):
    """registry for generic types. for example :class:`~typing.List`.

    These types must have ``__origin__`` and ``__args__`` attributes
    """
    registry: t.Mapping[
        t.Type[T],
        t.Callable[[t.Tuple[type], t.Any, Registry], T]] = _dictfield()

    def __call__(self, cls: t.Type[T], main: Registry=None) -> T:
        if not hasattr(cls, '__origin__'):
            raise UnsupportedType(cls)
        try:
            return partial(self.registry[cls.__origin__],
                           list(map(main or self, cls.__args__)))
        except KeyError:
            raise UnsupportedType(cls)


class UnsupportedType(LookupError):
    """indicates the loader cannot load the given type"""


def create_dataclass_loader(cls, registry, sourcemap=None):
    """create a loader for a dataclass type"""
    fields = valmap(attrgetter('type'), cls.__dataclass_fields__)
    sourcemap = {**dict(zip(fields, fields)), **(sourcemap or {})}
    sources = map(sourcemap.__getitem__, fields)
    typeinfos = map(_deconstruct_type, fields.values())

    itemgetters = (
        partial(getitem, key=source, multiple=multiple, optional=optional)
        for source, (_, multiple, optional) in zip(sources, typeinfos)
    )
    loaders = map(registry, fields.values())
    getters = list(starmap(compose, zip(loaders, itemgetters)))

    def dloader(obj):
        return cls(*(g(obj) for g in getters))

    return dloader


def list_loader(subloaders, value):
    """loader for the List generic"""
    loader, = subloaders
    return list(map(loader, value))


def set_loader(subloaders, value):
    """loader for the Set generic"""
    loader, = subloaders
    return set(map(loader, value))


def get_optional_loader(cls: t.Type[T], main: Registry) -> Loader[T]:
    """a combinable registry for optional types"""
    if _is_optional_type(cls):
        return partial(_optional_loader, main(cls.__args__[0]))
    else:
        raise UnsupportedType(cls)


def _optional_loader(subloader, value):
    return value if value is None else subloader(value)


@dataclass(frozen=True)
class AutoDataclassRegistry(CombinableRegistry):
    """loader which attempts to load dataclasses with defaults"""

    def __call__(self, cls, main=None):
        if hasattr(cls, '__dataclass_fields__'):
            return create_dataclass_loader(cls, main or self)
        else:
            raise UnsupportedType(cls)


simple_registry = PrimitiveRegistry({
    int:        int,
    float:      float,
    str:        str,
    bool:       bool,
    type(None): identity,
    datetime:   dateutil.parser.parse,
    object:     identity,
}) | GenericRegistry({
    t.List:   list_loader,
    t.Set:    set_loader,
}) | get_optional_loader | AutoDataclassRegistry()


@singledispatch
def getitem(obj, key: str, multiple: bool, optional: bool):
    """get a value from a data structure"""
    raise TypeError(obj)


@getitem.register(collections.Mapping)
def _json_getitem(obj, key, multiple, optional):
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


def _is_optional_type(cls):
    """determine whether a class is an Optional[...] type"""
    try:
        return (cls.__origin__ is t.Union
                and len(cls.__args__) == 2
                and cls.__args__[1] is NoneType)
    except AttributeError:
        return False


def _is_collection_type(cls):
    """determine whether a class is a generic collection type"""
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
