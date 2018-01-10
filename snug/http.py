"""basic HTTP tools"""
import typing as t
import urllib.request
from base64 import b64encode
from dataclasses import field, replace
from functools import partial
from operator import methodcaller

from . import asnc
from .core import Sender, compose, execute, Executor
from .utils import dclass

__all__ = ['Request', 'GET', 'Response', 'urllib_sender']

_dictfield = partial(field, default_factory=dict)
Headers = t.Mapping[str, str]


@dclass
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
    method:  str
    url:     str
    data:    t.Optional[bytes] = None
    params:  t.Mapping[str, str] = _dictfield()
    headers: Headers = _dictfield()

    def with_headers(self, headers: Headers) -> 'Request':
        """new request with added headers

        Parameters
        ----------
        headers
            the headers to add
        """
        return replace(self, headers={**self.headers, **headers})

    def with_prefix(self, prefix: str) -> 'Request':
        """new request with added url prefix

        Parameters
        ----------
        prefix
            the URL prefix
        """
        return replace(self, url=prefix + self.url)

    def with_params(self, params: t.Mapping[str, str]) -> 'Request':
        """new request with added params

        Parameters
        ----------
        params
            the parameters to add
        """
        return replace(self, params={**self.params, **params})

    def with_basic_auth(self, credentials: t.Tuple[str, str]) -> 'Request':
        """new request with "basic" authentication

        Parameters
        ----------
        credentials
            the username-password pair
        """
        username, password = credentials
        encoded = b64encode(f'{username}:{password}'.encode('ascii'))
        return self.with_headers({
            'Authorization': f'Basic {encoded.decode("ascii")}'})

    replace = replace


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


@dclass
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
    status_code: int
    data:        t.Optional[bytes] = None
    headers:     Headers = field(default_factory=dict)


def urllib_sender(**kwargs) -> Sender[Request, Response]:
    """create a :class:`~snug.Sender` using :mod:`urllib`.

    Parameters
    ----------
    **kwargs
        parameters passed to :func:`urllib.request.urlopen`
    """
    def _urllib_send(req: Request) -> Response:
        url = f'{req.url}?{urllib.parse.urlencode(req.params)}'
        raw_request = urllib.request.Request(url, headers=req.headers,
                                             method=req.method)
        raw_response = urllib.request.urlopen(raw_request, **kwargs)
        return Response(
            raw_response.getcode(),
            data=raw_response.read(),
            headers=raw_response.headers,
        )

    return _urllib_send


def simple_exec(sender: Sender[Request, Response]=urllib_sender()) -> (
        Executor[Request, Response]):
    """create a simple executor

    Parameters
    ----------
    sender
        the request sender
    """
    return partial(execute, sender=sender)


def authed_exec(auth: t.Tuple[str, str],
                sender: Sender[Request, Response]=urllib_sender()) -> (
                    Executor[Request, Response]):
    """create an authenticated executor

    Parameters
    ----------
    auth
        (username, password)-tuple
    sender
        the request sender
    """
    return partial(
        execute,
        sender=compose(sender, methodcaller('with_basic_auth', auth)))


def authed_aexec(auth: t.Tuple[str, str],
                 sender: asnc.Sender[Request, Response]) -> (
                     asnc.Executor[Request, Response]):
    """create an authenticated async executor

    Parameters
    ----------
    auth
        (username, password)-tuple
    sender
        the request sender
    """
    return partial(
        asnc.execute,
        sender=compose(sender, methodcaller('with_basic_auth', auth)))


try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    pass
else:
    def requests_sender(session: requests.Session) -> Sender[Request,
                                                             Response]:
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

    __all__.append('requests_sender')


try:
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover
    pass
else:
    def aiohttp_sender(session: aiohttp.ClientSession) -> asnc.Sender[Response,
                                                                      Request]:
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

    __all__.append('aiohttp_sender')
