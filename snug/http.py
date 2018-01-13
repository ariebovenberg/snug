"""basic HTTP tools"""
import typing as t
import urllib.request
from base64 import b64encode
from functools import partial
from operator import methodcaller

from . import asnc
from .core import Executor, Sender, compose, execute
from .utils import EMPTY_MAPPING

__all__ = ['Request', 'GET', 'Response', 'urllib_sender']

Headers = t.Mapping[str, str]


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

    def with_headers(self, headers: Headers) -> 'Request':
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

    def replace(self, **kwargs):
        return Response(**{**self._asdict(), **kwargs})


def urllib_sender(**kwargs) -> Sender[Request, Response]:
    """create a :class:`~snug.Sender` using :mod:`urllib`.

    Parameters
    ----------
    **kwargs
        parameters passed to :func:`urllib.request.urlopen`
    """
    def _urllib_send(req: Request) -> Response:
        url = req.url + '?' + urllib.parse.urlencode(req.params)
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
except ImportError:  # pragma: no cover
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
except ImportError:  # pragma: no cover
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
