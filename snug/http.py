"""Basic HTTP abstractions and functionality"""
from base64 import b64encode
from collections import Mapping
from functools import partial
from itertools import chain, starmap
from operator import attrgetter, methodcaller

_TextMapping = Mapping


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
    'Headers',
]


# why a dedicated class?
# - it allows us to deal with headers in a case-insensitive manner
# - it allows us to make it immutable which is easier to reason about.
# - it may be hashable, allowing Request to be hashable
class Headers(Mapping):
    """Case-insensitive, immutable, hashable mapping of headers"""
    __slots__ = '_inner', '_casing'

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

    def __hash__(self):
        return hash(frozenset(self._inner.items()))


class Request:
    """A simple HTTP request.

    Parameters
    ----------
    method: str
        The http method
    url: str
        The requested url
    content: bytes or None
        The request content
    params: Mapping
        The query parameters
    headers: Mapping
        request headers
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method, url, content=None, params=None,
                 headers=Headers()):
        self.method = method
        self.url = url
        self.content = content
        self.params = params or {}
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
        params: Mapping
            the parameters to add
        """
        merged = dict(chain(self.params.items(), params.items()))
        return self.replace(params=merged)

    def _asdict(self):
        return {a: getattr(self, a) for a in self.__slots__}

    def __eq__(self, other):
        if isinstance(other, Request):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Request):
            return self._asdict() != other._asdict()
        return NotImplemented

    def replace(self, **kwargs):
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace

        Returns
        -------
        Request
            the new request
        """
        attrs = self._asdict()
        attrs.update(kwargs)
        return Request(**attrs)

    def __repr__(self):
        return ('<Request: {0.method} {0.url}, params={0.params!r}, '
                'headers={0.headers!r}>').format(self)


class Response:
    """A simple HTTP response.

    Parameters
    ----------
    status_code: int
        The HTTP status code
    content: bytes or None
        The response content
    headers: Mapping
        The headers of the response. Defaults to an empty :class:`dict`.
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code, content=None, headers=Headers()):
        self.status_code = status_code
        self.content = content
        self.headers = headers

    def _asdict(self):
        return {a: getattr(self, a) for a in self.__slots__}

    def __eq__(self, other):
        if isinstance(other, Response):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Response):
            return self._asdict() != other._asdict()
        return NotImplemented

    def __repr__(self):
        return ('<Response: {0.status_code}, '
                'headers={0.headers!r}>').format(self)

    def replace(self, **kwargs):
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace

        Returns
        -------
        Response
            the resulting response
        """
        attrs = self._asdict()
        attrs.update(kwargs)
        return Response(**attrs)


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
