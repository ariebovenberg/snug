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
    'Relation',
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
    """a simple HTTP request

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
        """new request with added headers

        Parameters
        ----------
        headers
            the headers to add
        """
        merged = dict(chain(self.headers.items(), headers.items()))
        return self.replace(headers=merged)

    def with_prefix(self, prefix: str) -> 'Request':
        """new request with added url prefix

        Parameters
        ----------
        prefix
            the URL prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params: TextMapping) -> 'Request':
        """new request with added params

        Parameters
        ----------
        params
            the parameters to add
        """
        merged = dict(chain(self.params.items(), params.items()))
        return self.replace(params=merged)

    def with_basic_auth(self, credentials: t.Tuple[str, str]) -> 'Request':
        """new request with "basic" authentication

        Parameters
        ----------
        credentials
            the username-password pair
        """
        encoded = b64encode(':'.join(credentials).encode('ascii')).decode()
        return self.with_headers({'Authorization': 'Basic ' + encoded})

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
        """create a copy with replaced fields

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
    """a simple HTTP response

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
        """create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace
        """
        attrs = self._asdict()
        attrs.update(kwargs)
        return Response(**attrs)


class _CallableAsMethod:
    """mixin for callables to be callable as methods when bound to a class"""
    def __get__(self, obj, objtype=None):
        return self if obj is None else MethodType(self, obj)


class Query(t.Generic[T], t.Iterable[Request]):
    """ABC for query-like objects.
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


class RelationMeta(type(Query), _CallableAsMethod):
    pass


class Relation(Query[T], metaclass=RelationMeta):
    """:class:`Relation` subclasses act like a method
    when bound to a class. This means the parent instance is passed
    as a first argument when calling the class.

    This can be used to implement related queries

    Example
    -------

    >>> class Parent:
    ...     class child(Relation):
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


Sender = t.Callable[[Request], Response]
AsyncSender = t.Callable[[Request], Awaitable(Response)]
Executor = t.Callable[[Query[T]], T]
AsyncExecutor = t.Callable[[Query[T]], Awaitable(T)]
AuthenticatorFactory = t.Callable[[T_auth], t.Callable[[Request], Request]]


def urllib_sender(req: Request, **kwargs) -> Response:
    """simple sender which uses python's :mod:`urllib`

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


class _SocketAdapter:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


@asyncio.coroutine
def asyncio_sender(req: Request) -> Awaitable(Response):
    """a very rudimentary HTTP client using asyncio"""
    if 'User-Agent' not in req.headers:
        req = req.with_headers({'User-Agent': _ASYNCIO_USER_AGENT})
    url = urllib.parse.urlsplit(
        req.url + '?' + urllib.parse.urlencode(req.params))
    if url.scheme == 'https':
        connect = asyncio.open_connection(url.hostname, 443, ssl=True)
    else:
        connect = asyncio.open_connection(url.hostname, 80)
    reader, writer = yield from connect

    headers = '\r\n'.join([
        '{} {} HTTP/1.1'.format(req.method, url.path + '?' + url.query),
        'Host: ' + url.hostname,
        'Connection: close',
        'Content-Length: {}'.format(len(req.content or b'')),
        '\r\n'.join(starmap('{}: {}'.format, req.headers.items())),
    ])
    writer.write(b'\r\n'.join([headers.encode(), b'', req.content or b'']))
    response_bytes = BytesIO((yield from reader.read()))
    writer.close()
    raw_response = HTTPResponse(_SocketAdapter(response_bytes))
    raw_response.begin()
    return Response(
        raw_response.getcode(),
        content=raw_response.read(),
        headers=raw_response.headers,
    )


def _basic_auth_factory(auth):
    return methodcaller('with_basic_auth', auth)


@singledispatch
def make_sender(client) -> Sender:
    """Create a sender for the given client.
    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        the client to create a sender from

    Note
    ----
    if `requests <http://docs.python-requests.org/>`_ is installed,
    :class:`requests.Session` is already registerd.
    """
    raise TypeError('no sender factory registered for {!r}'.format(client))


@singledispatch
def make_async_sender(client) -> AsyncSender:
    """create an asynchronous sender from the given client.
    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        the client to create a sender from

    Note
    ----
    if `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed,
    :class:`aiohttp.ClientSession` is already registerd.
    """
    raise TypeError(
        'no async sender factory registered for {!r}'.format(client))


# useful shortcuts
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


def execute(query: Query[T], sender: Sender=urllib_sender) -> T:
    """execute a query

    Parameters
    ----------
    query
        the query to resolve
    sender
        the sender to use
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
def execute_async(query: Query[T],
                  sender: AsyncSender=asyncio_sender) -> Awaitable(T):
    """execute a query asynchronously

    Parameters
    ----------
    query
        the query to resolve
    sender
        the sender to use

    Note
    ----
    The default sender is very rudimentary.
    Consider using :func:`~snug.core.make_async_sender` to construct a
    sender from :class:`aiohttp.ClientSession` objects.
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = yield from sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


def executor(auth: T_auth=None,
             client=None,
             auth_factory: AuthenticatorFactory=_basic_auth_factory) -> (
                 t.Callable[[Query[T]], T]):
    """create an executor

    Parameters
    ----------
    auth
        the credentials
    client
        The HTTP client to use.
        Its type must have been registered
        with the :func:`~snug.core.make_sender` function.
    auth_factory
        the authentication method to use
    """
    _sender = urllib_sender if client is None else make_sender(client)
    authenticator = identity if auth is None else auth_factory(auth)
    return partial(execute, sender=compose(_sender, authenticator))


def async_executor(
        auth: T_auth=None,
        client=None,
        auth_factory: AuthenticatorFactory=_basic_auth_factory) -> (
            AsyncExecutor):
    """create an ascynchronous executor

    Parameters
    ----------
    auth
        the credentials
    client
        The (asynchronous) HTTP client to use.
        Its type must have been registered
        with the :func:`~snug.core.make_async_sender` function.
    auth_factory
        the authentication method to use
    """
    _sender = asyncio_sender if client is None else make_async_sender(client)
    authenticator = identity if auth is None else auth_factory(auth)
    return partial(execute_async, sender=compose(_sender, authenticator))


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:
    @make_async_sender.register(aiohttp.ClientSession)
    def _aiohttp_sender(session: aiohttp.ClientSession):
        """create an asynchronous sender
        for an `aiohttp` client session

        Parameters
        ----------
        session
            the aiohttp session
        """
        from snug.core import Response

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
    def _requests_sender(session: requests.Session):
        """create a :class:`~snug.Sender` for a :class:`requests.Session`

        Parameters
        ----------
        session
            a requests session

        Returns
        -------
        Sender
            a request sender
        """

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
