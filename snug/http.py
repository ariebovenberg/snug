"""Basic HTTP abstractions and functionality"""
import abc
from base64 import b64encode
from collections import (Mapping, OrderedDict, Counter, Sequence, Iterable,
                         Sized)
from functools import partial
from itertools import chain, starmap
from operator import attrgetter, methodcaller

from .compat import singledispatch

__all__ = [
    'Request',
    'Response',
    'header_adder',
    'prefix_adder',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
    'as_queryparams',
    'Headers',
    'QueryParams',
    'OrderedQueryParams',
    'UnorderedQueryParams'
]


class QueryParams(Iterable, Sized):
    """an immutable, possibly ordered, non-unique set of query parameters"""
    __slots__ = ()
    __hash__ = None

    @abc.abstractmethod
    def __len__(self):
        """The number of query parameters"""
        raise NotImplementedError()

    @abc.abstractmethod
    def __iter__(self):
        """Iterate over the key-value pairs"""
        raise NotImplementedError()

    def __ne__(self, other):
        equality = self.__eq__(other)
        return NotImplemented if equality is NotImplemented else not equality


class UnorderedQueryParams(QueryParams):
    __slots__ = '_items'

    def __init__(self, items):
        self._items = Counter(items)

    def __iter__(self):
        return iter(self._items.elements())

    def __len__(self):
        return sum(self._items.values())

    def __eq__(self, other):
        if isinstance(other, Mapping):
            return self._items == Counter(other.items())
        elif isinstance(other, UnorderedQueryParams):
            return self._items == other._items
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Mapping):
            return UnorderedQueryParams(self._items + Counter(other.items()))
        if isinstance(other, UnorderedQueryParams):
            return UnorderedQueryParams(self._items + other._items)
        return NotImplemented

    def __repr__(self):
        content = ' & '.join(map('='.join, self))
        return '{{{}}}'.format(content or '<empty>')


class OrderedQueryParams(QueryParams):
    __slots__ = '_items'

    def __init__(self, items):
        self._items = tuple(items)

    __iter__ = property(attrgetter('_items.__iter__'))
    __len__ = property(attrgetter('_items.__len__'))

    def __eq__(self, other):
        if isinstance(other, Sequence):
            return self._items == tuple(other)
        if isinstance(other, OrderedQueryParams):
            return self._items == other._items
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, (tuple, list)):
            return OrderedQueryParams(self._items + tuple(other))
        if isinstance(other, OrderedQueryParams):
            return OrderedQueryParams(self._items + other._items)
        return NotImplemented

    def __repr__(self):
        content = ' & '.join(map('='.join, self))
        return '[{}]'.format(content or '<empty>')


@singledispatch
def as_queryparams(obj):
    if isinstance(obj, Mapping):
        return UnorderedQueryParams(obj.items())
    return OrderedQueryParams(iter(obj))


@as_queryparams.register(OrderedDict)
def _odict_as_queryparams(obj):
    return OrderedQueryParams(obj.items())


as_queryparams.register(Counter, UnorderedQueryParams)
as_queryparams.register(QueryParams, lambda x: x)


class Headers(Mapping):
    """Case-insensitive, immutable, mapping of headers"""
    __slots__ = '_inner', '_casing'
    __hash__ = None

    def __init__(self, items=()):
        inner = dict(items)
        self._casing = {k.lower(): k for k in inner}
        self._inner = {k.lower(): v for k, v in inner.items()}

    def __getitem__(self, name):
        return self._inner[name.lower()]

    __len__ = property(attrgetter('_inner.__len__'))

    def __iter__(self):
        return iter(self._casing.values())

    def __repr__(self):
        content = ', '.join(starmap(
            '{}: {!r}'.format,
            zip(self._casing.values(),
                self._inner.values()))) if self else '<empty>'
        return '{{{}}}'.format(content)

    def __eq__(self, other):
        if isinstance(other, Mapping):
            return self._inner == Headers(other)._inner
        return NotImplemented


class _SlotsMixin(object):
    __slots__ = ()

    def _asdict(self):
        return OrderedDict((a, getattr(self, a)) for a in self.__slots__)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self._asdict() != other._asdict()
        return NotImplemented

    def replace(self, **kwargs):
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace
        """
        merged = dict(chain(self._asdict().items(), kwargs.items()))
        return self.__class__(**merged)


class Request(_SlotsMixin):
    """A simple HTTP request.

    Parameters
    ----------
    method: str
        The http method
    url: str
        The requested url
    content: bytes or None
        The request content
    params: ~typing.Mapping[str, str] or ~typing.Iterable[(str, str)] \
            or QueryParams
        The query parameters. If given an :class:`~collections.OrderedDict`
        or iterable, becomes order-sensitive.
    headers: Mapping
        request headers
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method, url, content=None,
                 params=UnorderedQueryParams({}),
                 headers=Headers()):
        self.method = method
        self.url = url
        self.content = content
        self.params = as_queryparams(params)
        self.headers = headers

    def with_headers(self, headers):
        """Create a new request with added headers

        Parameters
        ----------
        headers: Mapping
            the headers to add
        """
        merged = dict(chain(self.headers.items(), headers.items()))
        return self.replace(headers=merged)

    def with_prefix(self, prefix):
        """Create a new request with added url prefix

        Parameters
        ----------
        prefix: str
            the URL prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params):
        """Create a new request with added params

        Parameters
        ----------
        params: ~typing.Mapping[str, str] or ~typing.Iterable[(str, str)] \
                or QueryParams
        """
        return self.replace(params=self.params + as_queryparams(params))

    def __repr__(self):
        return ('<Request: {0.method} {0.url}, params={0.params!r}, '
                'headers={0.headers!r}>').format(self)


class Response(_SlotsMixin):
    """A simple HTTP response.

    Parameters
    ----------
    status_code: int
        The HTTP status code
    content: bytes or None
        The response content
    headers: Mapping
        The headers of the response.
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code, content=None, headers=Headers()):
        self.status_code = status_code
        self.content = content
        self.headers = headers

    def __repr__(self):
        return ('<Response: {0.status_code}, '
                'headers={0.headers!r}>').format(self)


def basic_auth(credentials, request):
    """Apply basic authentication to a request"""
    encoded = b64encode(':'.join(credentials).encode('ascii')).decode()
    return request.with_headers({'Authorization': 'Basic ' + encoded})


prefix_adder = partial(methodcaller, 'with_prefix')
prefix_adder.__doc__ = "make a callable which adds a prefix to a request url"
header_adder = partial(methodcaller, 'with_headers')
header_adder.__doc__ = "make a callable which adds headers to a request"
GET = partial(Request, 'GET')
GET.__doc__ = "shortcut for a GET request"
POST = partial(Request, 'POST')
POST.__doc__ = "shortcut for a POST request"
PUT = partial(Request, 'PUT')
PUT.__doc__ = "shortcut for a PUT request"
PATCH = partial(Request, 'PATCH')
PATCH.__doc__ = "shortcut for a PATCH request"
DELETE = partial(Request, 'DELETE')
DELETE.__doc__ = "shortcut for a DELETE request"
HEAD = partial(Request, 'HEAD')
HEAD.__doc__ = "shortcut for a HEAD request"
OPTIONS = partial(Request, 'OPTIONS')
OPTIONS.__doc__ = "shortcut for a OPTIONS request"
