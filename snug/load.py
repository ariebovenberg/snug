"""Tools for deserialization

Todo
----
* resolve forward declarations in dataclass signatures
* auto namedtuple registry
"""
import abc
import typing as t
from datetime import datetime
from functools import partial
from itertools import starmap
from operator import attrgetter, itemgetter

from dataclasses import dataclass, field
from toolz import valmap, compose, identity

from .utils import lookup_defaults, parse_iso8601

__all__ = ['Registry', 'Loader', 'CombinableRegistry', 'MultiRegistry',
           'PrimitiveRegistry', 'GenericRegistry', 'AutoDataclassRegistry',
           'create_dataclass_loader', 'list_loader', 'set_loader',
           'get_optional_loader', 'simple_registry']

T = t.TypeVar('T')
NoneType = type(None)
_dictfield = partial(field, default_factory=dict)


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
    """indicates the registry does not have a loader for the given type"""


def create_dataclass_loader(cls, registry, field_getters):
    """create a loader for a dataclass type"""
    fields = valmap(attrgetter('type'), cls.__dataclass_fields__)
    getters = map(field_getters.__getitem__, fields)
    optionals = map(_is_optional_type, fields.values())

    # coverage examption here because branch coverage
    # cannot tell if the generator is fully consumed by zip().
    itemgetters = (  # pragma: no cover
        lookup_defaults(getter, None) if optional else getter
        for getter, optional in zip(getters, optionals)
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
    """registry which creates dataclass loaders on-the-fly"""

    def __call__(self, cls, main):
        if hasattr(cls, '__dataclass_fields__'):
            return create_dataclass_loader(cls, main, {
                f: itemgetter(f) for f in cls.__dataclass_fields__
            })
        else:
            raise UnsupportedType(cls)


@dataclass(frozen=True)
class DataclassRegistry(CombinableRegistry):
    """registry for dataclasses"""
    confs: t.Mapping[t.Type[T], t.Mapping[str, str]]

    def __call__(self, cls, main):
        try:
            sourcemap = self.confs[cls]
        except KeyError:
            raise UnsupportedType(cls)
        return create_dataclass_loader(cls, main, sourcemap)


simple_registry = PrimitiveRegistry({
    int:        int,
    float:      float,
    str:        str,
    bool:       bool,
    type(None): identity,
    datetime:   parse_iso8601,
    object:     identity,
}) | GenericRegistry({
    t.List:   list_loader,
    t.Set:    set_loader,
}) | get_optional_loader | AutoDataclassRegistry()


def _is_optional_type(cls):
    """determine whether a class is an Optional[...] type"""
    try:
        return (cls.__origin__ is t.Union
                and len(cls.__args__) == 2
                and cls.__args__[1] is NoneType)
    except AttributeError:
        return False
