"""Basic HTTP abstractions and functionality"""
import asyncio
import sys
import typing as t
from base64 import b64encode
from functools import partial, singledispatch
from itertools import starmap, chain
from operator import attrgetter, methodcaller

from collections import Mapping

_TextMapping = Mapping
_Awaitable = (t.Awaitable.__getitem__  # pragma: no cover
              if sys.version_info > (3, 5)
              else lambda x: t.Generator[t.Any, t.Any, x])


__all__ = [
    'Request',
    'Response',
    'send',
    'send_async',
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

    def __getitem__(self, name: str):
        return self._inner[name.lower()]

    __len__ = property(attrgetter('_inner.__len__'))

    def __iter__(self):
        yield from self._casing.values()

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
    method
        The http method
    url
        The requested url
    content
        The request content
    params
        The query parameters
    headers
        request headers
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method: str, url: str, content: bytes=None, *,
                 params: _TextMapping=None,
                 headers: _TextMapping=Headers()):
        self.method = method
        self.url = url
        self.content = content
        self.params = params or {}
        self.headers = headers

    def with_headers(self, headers: _TextMapping) -> 'Request':
        """Create a new request with added headers

        Parameters
        ----------
        headers
            the headers to add
        """
        merged = dict(chain(self.headers.items(), headers.items()))
        return self.replace(headers=merged)

    def with_prefix(self, prefix: str) -> 'Request':
        """Create a new request with added url prefix

        Parameters
        ----------
        prefix
            the URL prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params: _TextMapping) -> 'Request':
        """Create a new request with added params

        Parameters
        ----------
        params
            the parameters to add
        """
        merged = dict(chain(self.params.items(), params.items()))
        return self.replace(params=merged)

    def _asdict(self):
        return {a: getattr(self, a) for a in self.__slots__}

    def __eq__(self, other):
        """check for equality with another request"""
        if isinstance(other, Request):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        """check for inequality with another request"""
        if isinstance(other, Request):
            return self._asdict() != other._asdict()
        return NotImplemented

    def replace(self, **kwargs) -> 'Request':
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace
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
    status_code
        The HTTP status code
    content
        The response content
    headers
        The headers of the response. Defaults to an empty :class:`dict`.
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code: int, content: bytes=None, *,
                 headers: _TextMapping=None):
        self.status_code = status_code
        self.content = content
        self.headers = {} if headers is None else headers

    def _asdict(self):
        return {a: getattr(self, a) for a in self.__slots__}

    def __eq__(self, other):
        """check for equality with another response"""
        if isinstance(other, Response):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        """check for inequality with another response"""
        if isinstance(other, Response):
            return self._asdict() != other._asdict()
        return NotImplemented

    def __repr__(self):
        return ('<Response: {0.status_code}, '
                'headers={0.headers!r}>').format(self)

    def replace(self, **kwargs) -> 'Response':
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace
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


@singledispatch
def send(client, request: Request) -> Response:
    """Given a client, send a :class:`Request`,
    returning a :class:`Response`.

    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        The client with which to send the request.

        Client types registered by default:

        * :class:`urllib.request.OpenerDirector`
          (e.g. from :func:`~urllib.request.build_opener`)
        * :class:`requests.Session`
          (if `requests <http://docs.python-requests.org/>`_ is installed)

    request
        The request to send


    Example of registering a new HTTP client:

    >>> @send.register(MyClientClass)
    ... def _send(client, request: Request) -> Response:
    ...     r = client.send(request)
    ...     return Response(r.status, r.read(), headers=r.get_headers())
    """
    raise TypeError('client {!r} not registered'.format(client))


@singledispatch
@asyncio.coroutine
def send_async(client, request: Request) -> _Awaitable(Response):
    """Given a client, send a :class:`Request`,
    returning an awaitable :class:`Response`.

    A :func:`~functools.singledispatch` function.

    Example of registering a new HTTP client:

    >>> @send_async.register(MyClientClass)
    ... async def _send(client, request: Request) -> Response:
    ...     r = await client.send(request)
    ...     return Response(r.status, r.read(), headers=r.get_headers())

    Parameters
    ----------
    client: any registered client type
        The client with which to send the request.

        Client types supported by default:

        * :class:`asyncio.AbstractEventLoop`
          (e.g. from :func:`~asyncio.get_event_loop`)
        * :class:`aiohttp.ClientSession`
          (if `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed)

        Note
        ----
        ``aiohttp`` is only supported on python 3.5.3+

    request
        The request to send
    """
    raise TypeError('client {!r} not registered'.format(client))
