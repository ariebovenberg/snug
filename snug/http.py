"""basic HTTP tools"""
import typing as t
import urllib.request
from base64 import b64encode
from functools import partial, singledispatch
from operator import methodcaller

from .core import (Executor as _Executor,
                   Sender as _Sender,
                   execute, AsyncExecutor as _AsyncExecutor, 
                   execute_async)
from . import core
from .utils import EMPTY_MAPPING, identity, compose

__all__ = [
    'Request',
    'Response',
    'executor',
    'async_executor',
    'urllib_sender',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
]


T_auth = t.TypeVar('T_auth')


class Request:
    """a simple HTTP request

    Parameters
    ----------
    method
        the http method
    url
        the requested url
    data
        the request content
    params
        the query parameters
    headers
        mapping of headers
    """
    __slots__ = 'method', 'url', 'data', 'params', 'headers'
    __hash__ = None

    def __init__(self,
                 method:  str,
                 url:     str,
                 data:    t.Optional[bytes]=None,
                 params:  t.Mapping[str, str]=EMPTY_MAPPING,
                 headers: t.Mapping[str, str]=EMPTY_MAPPING):
        self.method = method
        self.url = url
        self.data = data
        self.params = params
        self.headers = headers

    def with_headers(self, headers: t.Mapping[str, str]) -> 'Request':
        """new request with added headers

        Parameters
        ----------
        headers
            the headers to add
        """
        return self.replace(headers={**self.headers, **headers})

    def with_prefix(self, prefix: str) -> 'Request':
        """new request with added url prefix

        Parameters
        ----------
        prefix
            the URL prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params: t.Mapping[str, str]) -> 'Request':
        """new request with added params

        Parameters
        ----------
        params
            the parameters to add
        """
        return self.replace(params={**self.params, **params})

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

    def replace(self, **kwargs):
        return Request(**{**self._asdict(), **kwargs})

    def __repr__(self):
        return ('<Request: {0.method} {0.url}, params={0.params!r}, '
                'headers={0.headers!r}>').format(self)


class Response:
    """a simple HTTP response

    Parameters
    ----------
    status_code
        the HTTP status code
    data
        the response content
    headers
        the headers of the response
    """
    __slots__ = 'status_code', 'data', 'headers'
    __hash__ = None

    def __init__(self,
                 status_code: int,
                 data:        t.Optional[bytes]=None,
                 headers:     t.Mapping[str, str]=EMPTY_MAPPING):
        self.status_code = status_code
        self.data = data
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
        return Response(**{**self._asdict(), **kwargs})


Sender = core.Sender[Request, Response]
Executor = core.Executor[Request, Response]
AsyncSender = core.AsyncSender[Request, Response]
AsyncExecutor = core.AsyncExecutor[Request, Response]


def urllib_sender(req: Request, **kwargs) -> Response:
    """simple :class:`~snug.http.Sender` which uses python's :mod:`urllib`"""
    url = req.url + '?' + urllib.parse.urlencode(req.params)
    raw_request = urllib.request.Request(url, headers=req.headers,
                                         method=req.method)
    raw_response = urllib.request.urlopen(raw_request, **kwargs)
    return Response(
        raw_response.getcode(),
        data=raw_response.read(),
        headers=raw_response.headers,
    )


def optional_basic_auth(credentials: t.Optional[t.Tuple[str, str]]) -> (
        t.Callable[[Request], Request]):
    """"""
    if credentials is None:
        return identity
    else:
        return methodcaller('with_basic_auth', credentials)


_Authenticator = t.Callable[[T_auth], t.Callable[[Request], Request]]


def executor(auth: T_auth=None,
             client=None,
             authenticator: _Authenticator=optional_basic_auth) -> Executor:
    """create an executor

    Parameters
    ----------
    auth
        the credentials
    client
        The HTTP client to use.
    authenticator
        the authentication method to use
    """
    _sender = urllib_sender if client is None else sender(client)
    return partial(execute, sender=compose(_sender,
                                           authenticator(auth)))


def async_executor(
        auth: T_auth=None,
        client=None,
        authenticator: _Authenticator=optional_basic_auth) -> AsyncExecutor:
    """create an ascynchronous executor

    Parameters
    ----------
    auth
        the credentials
    client
        The (asynchronous) HTTP client to use.
    authenticator
        the authentication method to use
    """
    return partial(execute_async, sender=compose(async_sender(client),
                                                 authenticator(auth)))


@singledispatch
def sender(client) -> Sender:
    """create a sender for the given client"""
    raise TypeError('no sender factory registered for {!r}'.format(client))


@singledispatch
def async_sender(client) -> AsyncSender:
    """create an asynchronous sender from the given client"""
    raise TypeError(
        'no async sender factory registered for {!r}'.format(client))


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @sender.register(requests.Session)
    def _requests_sender(session: requests.Session) -> Sender:
        """create a :class:`~snug.Sender` for a :class:`requests.Session`

        Parameters
        ----------
        session
            a requests session
        """

        def _req_send(req: Request) -> Response:
            response = session.request(req.method, req.url,
                                       params=req.params,
                                       headers=req.headers)
            return Response(
                response.status_code,
                response.content,
                response.headers,
            )

        return _req_send


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:
    @async_sender.register(aiohttp.ClientSession)
    def _aiohttp_sender(session: aiohttp.ClientSession) -> AsyncSender:
        """create an asynchronous sender
        for an `aiohttp` client session

        Parameters
        ----------
        session
            the aiohttp session
        """
        async def _aiohttp_sender(req: Request) -> Response:
            async with session.request(req.method, req.url,
                                       params=req.params,
                                       data=req.data,
                                       headers=req.headers) as response:
                return Response(
                    response.status,
                    data=await response.read(),
                    headers=response.headers,
                )

        return _aiohttp_sender


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
