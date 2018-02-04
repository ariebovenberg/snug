import abc
import asyncio
import sys
import typing as t
import urllib.request
from base64 import b64encode
from functools import partial, singledispatch
from http.client import HTTPResponse
from io import BytesIO
from itertools import chain, starmap
from operator import methodcaller
from types import MethodType

from .utils import EMPTY_MAPPING, compose, identity

__all__ = [
    'Query',
    'execute',
    'execute_async',
    'executor',
    'async_executor',
    'Request',
    'Response',
    'related',
    'header_adder',
    'prefix_adder',
    'make_sender',
    'make_async_sender',
    'asyncio_sender',
    'urllib_sender',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
]

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
TextMapping = t.Mapping[str, str]
Awaitable = (t.Awaitable.__getitem__  # pragma: no cover
             if sys.version_info > (3, 5)
             else lambda x: t.Generator[t.Any, t.Any, x])
_ASYNCIO_USER_AGENT = 'Python-asyncio/3.{}'.format(sys.version_info.minor)


class Request:
    """A simple HTTP request

    Parameters
    ----------
    method
        the http method
    url
        the requested url
    content
        the request content
    params
        the query parameters
    headers
        mapping of headers
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method: str, url: str, content: bytes=None, *,
                 params: TextMapping=EMPTY_MAPPING,
                 headers: TextMapping=EMPTY_MAPPING):
        self.method = method
        self.url = url
        self.content = content
        self.params = params
        self.headers = headers

    def with_headers(self, headers: TextMapping) -> 'Request':
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

    def with_params(self, params: TextMapping) -> 'Request':
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
        if isinstance(other, Request):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
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
    """A simple HTTP response

    Parameters
    ----------
    status_code
        the HTTP status code
    content
        the response content
    headers
        the headers of the response
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code: int, content: bytes=None, *,
                 headers: TextMapping=EMPTY_MAPPING):
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


class Query(t.Generic[T], t.Iterable[Request]):
    """Abstract base class for query-like objects.
    Any object where :meth:`~object.__iter__`
    returns a :class:`Request`/:class:`Response` generator implements it.

    Note
    ----
    :term:`Generator iterator`\\s themselves also implement this interface
    (i.e. :meth:`~object.__iter__` returns the generator itself).
    """

    @abc.abstractmethod
    def __iter__(self) -> t.Generator[Request, Response, T]:
        """a generator which resolves the query"""
        raise NotImplementedError()


class related:
    """Decorate classes to make them callable as methods.
    This can be used to implement related queries.

    Example
    -------

    >>> class Parent:
    ...     @related
    ...     class child:
    ...         def __init__(self, parent, bar):
    ...             self.parent, self.bar = parent, bar
    ...         ...
    ...
    >>> p = Parent()
    >>> c = p.child(bar=5)
    >>> isinstance(c, Parent.child)
    True
    >>> c.parent is p
    True
    """
    def __init__(self, cls):
        self._cls = cls

    def __get__(self, obj, objtype=None):
        return self._cls if obj is None else MethodType(self._cls, obj)


_Sender = t.Callable[[Request], Response]
_AsyncSender = t.Callable[[Request], Awaitable(Response)]
_Executor = t.Callable[[Query[T]], T]
_AsyncExecutor = t.Callable[[Query[T]], Awaitable(T)]
_AuthMethod = t.Callable[[T_auth], t.Callable[[Request], Request]]


def urllib_sender(req: Request, **kwargs) -> Response:
    """Simple sender which uses :mod:`urllib`

    Parameters
    ----------
    req
        the request to send
    **kwargs
        keyword arguments passed to :func:`urllib.request.urlopen`
    """
    url = req.url + '?' + urllib.parse.urlencode(req.params)
    raw_request = urllib.request.Request(url, headers=req.headers,
                                         method=req.method)
    raw_response = urllib.request.urlopen(raw_request, **kwargs)
    return Response(
        raw_response.getcode(),
        content=raw_response.read(),
        headers=raw_response.headers,
    )


class _SocketAdaptor:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


@asyncio.coroutine
def asyncio_sender(req: Request) -> Awaitable(Response):
    """A rudimentary HTTP client using :mod:`asyncio`"""
    if 'User-Agent' not in req.headers:
        req = req.with_headers({'User-Agent': _ASYNCIO_USER_AGENT})
    url = urllib.parse.urlsplit(
        req.url + '?' + urllib.parse.urlencode(req.params))
    if url.scheme == 'https':
        connect = asyncio.open_connection(url.hostname, 443, ssl=True)
    else:
        connect = asyncio.open_connection(url.hostname, 80)
    reader, writer = yield from connect
    try:
        headers = '\r\n'.join([
            '{} {} HTTP/1.1'.format(req.method, url.path + '?' + url.query),
            'Host: ' + url.hostname,
            'Connection: close',
            'Content-Length: {}'.format(len(req.content or b'')),
            '\r\n'.join(starmap('{}: {}'.format, req.headers.items())),
        ])
        writer.write(b'\r\n'.join([headers.encode(), b'', req.content or b'']))
        response_bytes = BytesIO((yield from reader.read()))
    finally:
        writer.close()
    raw_response = HTTPResponse(_SocketAdaptor(response_bytes))
    raw_response.begin()
    return Response(
        raw_response.getcode(),
        content=raw_response.read(),
        headers=raw_response.headers,
    )


class BasicAuthenticator:
    """Basic authentication method

    Parameters
    ----------
    credentials
        the (username, password) pair
    """
    __slots__ = 'headers'

    def __init__(self, credentials: t.Tuple[str, str]):
        encoded = b64encode(':'.join(credentials)
                            .encode('ascii')).decode()
        self.headers = {'Authorization': 'Basic ' + encoded}

    def __call__(self, request: Request) -> Request:
        return request.with_headers(self.headers)


@singledispatch
def make_sender(client) -> _Sender:
    """Create a sender for the given client.
    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        the client to create a sender from

    Note
    ----
    if `requests <http://docs.python-requests.org/>`_ is installed,
    a sender for :class:`requests.Session` is already registerd.
    """
    raise TypeError('no sender factory registered for {!r}'.format(client))


@singledispatch
def make_async_sender(client) -> _AsyncSender:
    """Create an asynchronous sender from the given client.
    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        the client to create a sender from

    Note
    ----
    If `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed,
    a sender for :class:`aiohttp.ClientSession` is already registerd.
    """
    raise TypeError(
        'no async sender factory registered for {!r}'.format(client))


def execute(query: Query[T], *, sender: _Sender=urllib_sender) -> T:
    """Execute a query, returning its result

    Parameters
    ----------
    query
        the query to resolve
    sender
        the callable used to send requests, returning responses
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


@asyncio.coroutine
def execute_async(query: Query[T], *,
                  sender: _AsyncSender=asyncio_sender) -> Awaitable(T):
    """Execute a query asynchronously, returning its result

    Parameters
    ----------
    query
        the query to resolve
    sender
        the callable used to send requests, returning responses

    Note
    ----
    The default sender is very rudimentary.
    Consider using :func:`async_executor` to construct an
    executor from :class:`aiohttp.ClientSession` objects.
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = yield from sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


def executor(auth: T_auth=None, *,
             client=None,
             auth_method: _AuthMethod=BasicAuthenticator) -> _Executor:
    """Create an executor

    Parameters
    ----------
    auth
        the credentials
    client
        The HTTP client to use.
        Its type must have been registered
        with the :func:`make_sender` function.
    auth_method
        the authentication method to use
    """
    _sender = urllib_sender if client is None else make_sender(client)
    authenticator = identity if auth is None else auth_method(auth)
    return partial(execute, sender=compose(_sender, authenticator))


def async_executor(
        auth: T_auth=None, *,
        client=None,
        auth_method: _AuthMethod=BasicAuthenticator) -> _AsyncExecutor:
    """Create an ascynchronous executor

    Parameters
    ----------
    auth
        the credentials
    client
        The (asynchronous) HTTP client to use.
        Its type must have been registered
        with the :func:`make_async_sender` function.
    auth_method
        the authentication method to use
    """
    _sender = asyncio_sender if client is None else make_async_sender(client)
    authenticator = identity if auth is None else auth_method(auth)
    return partial(execute_async, sender=compose(_sender, authenticator))


prefix_adder = partial(methodcaller, 'with_prefix')
prefix_adder.__doc__ = """
make a callable which adds a prefix to a request url
"""
header_adder = partial(methodcaller, 'with_headers')
header_adder.__doc__ = """
make a callable which adds headers to a request
"""
GET = partial(Request, 'GET')
GET.__doc__ = """shortcut for a GET request"""
POST = partial(Request, 'POST')
POST.__doc__ = """shortcut for a POST request"""
PUT = partial(Request, 'PUT')
PUT.__doc__ = """shortcut for a PUT request"""
PATCH = partial(Request, 'PATCH')
PATCH.__doc__ = """shortcut for a PATCH request"""
DELETE = partial(Request, 'DELETE')
DELETE.__doc__ = """shortcut for a DELETE request"""
HEAD = partial(Request, 'HEAD')
HEAD.__doc__ = """shortcut for a HEAD request"""
OPTIONS = partial(Request, 'OPTIONS')
OPTIONS.__doc__ = """shortcut for a OPTIONS request"""


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:
    @make_async_sender.register(aiohttp.ClientSession)
    def _aiohttp_sender(session: aiohttp.ClientSession) -> _AsyncSender:
        """Create an asynchronous sender
        for an `aiohttp` client session"""
        @asyncio.coroutine
        def _aiohttp_sender(req):
            response = yield from session.request(req.method, req.url,
                                                  params=req.params,
                                                  data=req.content,
                                                  headers=req.headers)
            try:
                return Response(
                    response.status,
                    content=(yield from response.read()),
                    headers=response.headers,
                )
            except Exception:  # pragma: no cover
                response.close()
                raise
            finally:
                yield from response.release()

        return _aiohttp_sender


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @make_sender.register(requests.Session)
    def _requests_sender(session: requests.Session) -> _Sender:
        """Create a sender for a :class:`requests.Session`"""
        def _req_send(req: Request) -> Response:
            response = session.request(req.method, req.url,
                                       params=req.params,
                                       headers=req.headers)
            return Response(
                response.status_code,
                response.content,
                headers=response.headers,
            )
        return _req_send
