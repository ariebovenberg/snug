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

__version__ = '1.1.0'
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
        The query parameters. Defaults to an empty :class:`dict`.
    headers
        Mapping of headers. Defaults to an empty :class:`dict`.
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method: str, url: str, content: bytes=None, *,
                 params: _TextMapping=None,
                 headers: _TextMapping=None):
        self.method = method
        self.url = url
        self.content = content
        self.params = {} if params is None else params
        self.headers = {} if headers is None else headers

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

    Creating a class-based query:

    >>> # actually subclassing `Query` is not required
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

    Creating a fully customized query (for rare cases):

    >>> # actually subclassing `Query` is not required
    >>> class asset_download(snug.Query):
    ...     \"\"\"streaming download of a repository asset.
    ...     Can only be executed with particular clients\"\"\"
    ...     def __init__(self, repo_name, repo_owner, id):
    ...         self.request = snug.GET(
    ...             f'https://api.github.com/repos/{repo_owner}'
    ...             f'/{repo_name}/releases/assets/{id}',
    ...             headers={'Accept': 'application/octet-stream'})
    ...
    ...     def __execute__(self, client, authenticate):
    ...         \"\"\"execute, returning a streaming requests response\"\"\"
    ...         assert isinstance(client, requests.Session)
    ...         req = authenticate(self.request)
    ...         return client.request(req.method, req.url,
    ...                               data=req.content,
    ...                               params=req.params,
    ...                               headers=req.headers)
    ...
    ...     async def __execute_async__(self, client, authenticate):
    ...         ...
    ...
    >>> query = asset_download('hub', rep_owner='github', id=4187895)
    >>> response = snug.execute(download, client=requests.Session())
    >>> for chunk in response.iter_content():
    ...    ...
    """
    def __iter__(self) -> t.Generator[Request, Response, T]:
        """A generator iterator which resolves the query"""
        raise NotImplementedError()

    def __execute__(self, client,
                    authenticate: t.Callable[[Request], Request]) -> T:
        """Default execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute`
        authenticate
            a callable to authenticate a :class:`Request`
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = send(client, authenticate(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value

    @asyncio.coroutine
    def __execute_async__(self, client,
                          authenticate: t.Callable[[Request], Request]) -> T:
        """Default asynchronous execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute`
        authenticate
            a callable to authenticate a :class:`Request`
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = yield from send_async(client, authenticate(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value


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


class _SocketAdaptor:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


def basic_auth(credentials, request):
    """Apply basic authentication to a request"""
    encoded = b64encode(':'.join(credentials).encode('ascii')).decode()
    return request.with_headers({'Authorization': 'Basic ' + encoded})


def execute(query: Query[T], *,
            auth: T_auth=None,
            client=urllib.request.build_opener(),
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
        If not given, the built-in :mod:`urllib` module is used.
    auth_method
        the authentication method to use
    """
    exec_func = getattr(type(query), '__execute__', Query.__execute__)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


def execute_async(query: Query[T], *,
                  auth: T_auth=None,
                  client=asyncio.get_event_loop(),
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
        If not given, the built-in :mod:`asyncio` module is used.
    auth_method
        the authentication method to use

    Note
    ----
    The default client is very rudimentary.
    Consider using a :class:`aiohttp.ClientSession` instance as ``client``.
    """
    exec_func = getattr(
        type(query), '__execute_async__', Query.__execute_async__)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


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
    If `requests <http://docs.python-requests.org/>`_ is installed,
    :class:`requests.Session` is already registerd as a valid client type.
    """
    raise TypeError('client {!r} not registered'.format(client))


@send.register(urllib.request.OpenerDirector)
def _urllib_send(opener, req: Request, **kwargs) -> Response:
    """Send a request with an :mod:`urllib` opener"""
    if req.content and not any(h.lower() == 'content-type'
                               for h in req.headers):
        req = req.with_headers({'Content-Type': 'application/octet-stream'})
    url = req.url + '?' + urllib.parse.urlencode(req.params)
    raw_req = urllib.request.Request(url, req.content, headers=req.headers,
                                     method=req.method)
    res = urllib.request.urlopen(raw_req, **kwargs)
    return Response(res.getcode(), content=res.read(), headers=res.headers)


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
        the client with which to send the request
    request
        the request to send

    Note
    ----
    If `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed,
    :class:`aiohttp.ClientSession` is already registerd as a valid client type.
    """
    raise TypeError('client {!r} not registered'.format(client))


@send_async.register(asyncio.AbstractEventLoop)
@asyncio.coroutine
def _asyncio_send(loop, req: Request) -> _Awaitable(Response):
    """A rudimentary HTTP client using :mod:`asyncio`"""
    if not any(h.lower() == 'user-agent' for h in req.headers):
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
    resp = HTTPResponse(_SocketAdaptor(response_bytes))
    resp.begin()
    return Response(resp.getcode(), content=resp.read(), headers=resp.headers)


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


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:
    @send_async.register(aiohttp.ClientSession)
    @asyncio.coroutine
    def _aiohttp_send(session, req: Request) -> _Awaitable(Response):
        """send a request with the `aiohttp` library"""
        # this is basically a simplified `async with`
        # in py3.4 compatible syntax
        # see https://www.python.org/dev/peps/pep-0492/#new-syntax
        resp = yield from session.request(
            req.method, req.url,
            params=req.params,
            data=req.content,
            headers=req.headers).__aenter__()
        try:
            content = yield from resp.read()
        finally:
            yield from resp.__aexit__(None, None, None)
        return Response(resp.status, content=content, headers=resp.headers)


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @send.register(requests.Session)
    def _requests_send(session, req: Request) -> Response:
        """send a request with the `requests` library"""
        res = session.request(req.method, req.url,
                              data=req.content,
                              params=req.params,
                              headers=req.headers)
        return Response(res.status_code, res.content, headers=res.headers)
