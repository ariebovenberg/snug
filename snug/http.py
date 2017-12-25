"""basic HTTP tools"""
import typing as t
import urllib.request
from base64 import b64encode
from dataclasses import field, replace
from functools import partial

from . import asyn
from .core import Sender, T
from .utils import dclass

__all__ = ['Request', 'Response', 'urllib_sender']

_dictfield = partial(field, default_factory=dict)
Headers = t.Mapping[str, str]


@dclass
class Request(t.Generic[T]):
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
    data:    T = None
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


GET = partial(Request, 'GET')
"""shortcut for a GET request"""


@dclass
class Response(t.Generic[T]):
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
    data:        T = None
    headers:     Headers = field(default_factory=dict)


def urllib_sender(**kwargs) -> Sender[Request[bytes], Response[bytes]]:
    """create a :class:`Sender` using :mod:`urllib`.

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


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    def requests_sender(session: requests.Session) -> Sender[Request[bytes],
                                                             Response[bytes]]:
        """create a :class:`Sender` for a :class:`requests.Session`

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
    def aiohttp_sender(session: aiohttp.ClientSession) -> (
            asyn.Sender[Response[bytes], Request[bytes]]):
        """create a :class:`AsyncSender`
        for a :class:`aiohttp.ClientSession`

        Parameters
        ----------
        session
            a aiohttp session
        """
        async def _aiohttp_sender(req: Request[bytes]) -> (
                t.Awaitable[Response[bytes]]):
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
