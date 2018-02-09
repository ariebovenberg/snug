import abc
import asyncio
import sys
import typing as t
import urllib.request
from base64 import b64encode
from collections import Mapping
from functools import partial, singledispatch
from http.client import HTTPResponse
from io import BytesIO
from itertools import chain, starmap
from operator import methodcaller
from types import MethodType

__all__ = [
    'Query',
    'execute',
    'execute_async',
    'Request',
    'Response',
    'executor',
    'async_executor',
    'send',
    'send_async',
    'related',
    'header_adder',
    'prefix_adder',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
]

__version__ = '1.0.0'
__author__ = 'Arie Bovenberg'
__copyright__ = '2018, Arie Bovenberg'
__description__ = 'Write reusable web API interactions'

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
_TextMapping = t.Mapping[str, str]
_Awaitable = (t.Awaitable.__getitem__  # pragma: no cover
              if sys.version_info > (3, 5)
              else lambda x: t.Generator[t.Any, t.Any, x])
_ASYNCIO_USER_AGENT = 'Python-asyncio/3.{}'.format(sys.version_info.minor)
_Sender = t.Callable[['Request'], 'Response']
_AsyncSender = t.Callable[['Request'], _Awaitable('Response')]
_Executor = t.Callable[['Query[T]'], T]
_AExecutor = t.Callable[['Query[T]'], _Awaitable(T)]
_AuthMethod = t.Callable[[T_auth, 'Request'], 'Request']


def _identity(obj):
    return obj


class _compose:
    """compose a function from a chain of functions"""
    def __init__(self, *funcs):
        assert funcs
        self.funcs = funcs

    def __call__(self, *args, **kwargs):
        *tail, head = self.funcs
        value = head(*args, **kwargs)
        for func in reversed(tail):
            value = func(value)
        return value


class _EmptyMapping(Mapping):
    """an empty mapping to use as a default value"""
    def __iter__(self):
        yield from ()

    def __getitem__(self, key):
        raise KeyError(key)

    def __len__(self):
        return 0

    def __repr__(self):
        return '{<empty>}'


_EMPTY_MAPPING = _EmptyMapping()


class Request:
    """A simple HTTP request.

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
                 params: _TextMapping=_EMPTY_MAPPING,
                 headers: _TextMapping=_EMPTY_MAPPING):
        self.method = method
        self.url = url
        self.content = content
        self.params = params
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
        the HTTP status code
    content
        the response content
    headers
        the headers of the response
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code: int, content: bytes=None, *,
                 headers: _TextMapping=_EMPTY_MAPPING):
        self.status_code = status_code
        self.content = content
        self.headers = headers

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


class Query(t.Generic[T], t.Iterable[Request]):
    """Abstract base class for query-like objects.
    Any object whose :meth:`~object.__iter__`
    returns a :class:`Request`/:class:`Response` generator implements it.

    Note
    ----
    :term:`Generator iterator`\\s themselves also implement this interface
    (i.e. :meth:`~object.__iter__` returns the generator itself).

    Note
    ----
    Query is a :class:`~typing.Generic`.
    This means you may write ``Query[<returntype>]``
    as a descriptive type annotation.

    For example: ``Query[bool]`` indicates a query which returns a boolean.

    Examples
    --------

    Creating a query from a generator function:

    >>> def repo(name: str, owner: str) -> snug.Query[dict]:
    ...    \"\"\"a repo lookup by owner and name\"\"\"
    ...    req = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
    ...    response = yield req
    ...    return json.loads(response.content)
    ...
    >>> query = repo('Hello-World', owner='octocat')

    Creating a query with a :class:`Query` subclass:

    >>> class repo(snug.Query[dict]):
    ...    \"\"\"a repository lookup by owner and name\"\"\"
    ...    def __init__(self, name: str, owner: str):
    ...        self.name, self.owner = name, owner
    ...
    ...    def __iter__(self):
    ...        owner, name = self.owner, self.name
    ...        request = snug.GET(
    ...            f'https://api.github.com/repos/{owner}/{name}')
    ...        response = yield request
    ...        return json.loads(response.content)
    ...
    >>> query = repo('Hello-World', owner='octocat')
    """
    @abc.abstractmethod
    def __iter__(self) -> t.Generator[Request, Response, T]:
        """A generator iterator which resolves the query"""
        raise NotImplementedError()


class related:
    """Decorate classes to make them callable as methods.
    This can be used to implement related queries
    through nested classes.

    Example
    -------

    >>> class Foo:
    ...     @related
    ...     class Bar:
    ...         def __init__(self, foo, qux):
    ...             self.the_foo, self.qux = foo, qux
    ...         ...
    ...
    >>> f = Foo()
    >>> b = p.Bar(qux=5)
    >>> isinstance(b, Foo.Bar)
    True
    >>> b.the_foo is f
    True
    """
    def __init__(self, cls):
        self._cls = cls

    def __get__(self, obj, objtype=None):
        return self._cls if obj is None else MethodType(self._cls, obj)


def _urllib_sender(req: Request, **kwargs) -> Response:
    """Simple sender which uses :mod:`urllib`"""
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
def _asyncio_sender(req: Request) -> _Awaitable(Response):
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


def basic_auth(credentials, request):
    """Apply basic authentication to a request"""
    encoded = b64encode(':'.join(credentials).encode('ascii')).decode()
    return request.with_headers({
        'Authorization': 'Basic ' + encoded
    })


def _exec(query, sender):
    gen = iter(query)
    request = next(gen)
    while True:
        response = sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


@asyncio.coroutine
def _exec_async(query, sender):
    gen = iter(query)
    request = next(gen)
    while True:
        response = yield from sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


def execute(query: Query[T], *,
            auth: T_auth=None,
            client=None,
            auth_method: _AuthMethod=basic_auth) -> T:
    """Execute a query, returning its result

    Parameters
    ----------
    query
        the query to resolve
    auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`send`.
    auth_method
        the authentication method to use
    """
    sender = _urllib_sender if client is None else partial(send, client)
    authenticator = _identity if auth is None else partial(auth_method, auth)
    return _exec(query, sender=_compose(sender, authenticator))


def execute_async(query: Query[T], *,
                  auth: T_auth=None,
                  client=None,
                  auth_method: _AuthMethod=basic_auth) -> _Awaitable(T):
    """Execute a query asynchronously, returning its result

    Parameters
    ----------
    query
        the query to resolve
    auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`send_async`.
    auth_method
        the authentication method to use

    Note
    ----
    The default client is very rudimentary.
    Consider using a :class:`aiohttp.ClientSession` instance as ``client``.
    """
    sender = _asyncio_sender if client is None else partial(send_async, client)
    authenticator = _identity if auth is None else partial(auth_method, auth)
    return _exec_async(query, sender=_compose(sender, authenticator))


@singledispatch
def send(client, request: Request) -> Response:
    """Given a client, send a :class:`Request`,
    returning a :class:`Response`.

    A :func:`~functools.singledispatch` function.

    Example of registering a new HTTP client:

    >>> @send.register(MyClientClass)
    ... def _send(client, request: Request) -> Response:
    ...     r = client.send(request)
    ...     return Response(r.status, r.read(), headers=r.get_headers())

    Parameters
    ----------
    client: any registered client type
        the client with which to send the request
    request
        the request to send

    Note
    ----
    if `requests <http://docs.python-requests.org/>`_ is installed,
    :class:`requests.Session` is already registerd as a valid client type.
    """
    raise TypeError('client {!r} not registered'.format(client))


@singledispatch
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
        the client with which to send the request
    request
        the request to send

    Note
    ----
    If `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed,
    :class:`aiohttp.ClientSession` is already registerd as a valid client type.
    """
    raise TypeError('client {!r} not registered'.format(client))


def executor(**kwargs) -> _Executor:
    """Create a version of :func:`execute` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute`
    """
    return partial(execute, **kwargs)


def async_executor(**kwargs) -> _AExecutor:
    """Create a version of :func:`execute_async` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute_async`
    """
    return partial(execute_async, **kwargs)


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
    @send_async.register(aiohttp.ClientSession)
    @asyncio.coroutine
    def _aiohttp_send(session, req: Request) -> _Awaitable(Response):
        """send a request with the `aiohttp` library"""
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


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @send.register(requests.Session)
    def _requests_send(session, req: Request) -> Response:
        """send a request with the `requests` library"""
        response = session.request(req.method, req.url,
                                   data=req.content,
                                   params=req.params,
                                   headers=req.headers)
        return Response(
            response.status_code,
            response.content,
            headers=response.headers,
        )
