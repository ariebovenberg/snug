"""basic HTTP tools"""
import abc
import typing as t
import urllib.request
from base64 import b64encode
from dataclasses import dataclass, field, replace
from functools import partial

__all__ = ['Request', 'Response', 'Sender', 'AsyncSender', 'urllib_sender']

_dictfield = partial(field, default_factory=dict)
Headers = t.Mapping[str, str]

dclass = partial(dataclass, frozen=True)


@dclass
class Request:
    """a simple HTTP request

    Parameters
    ----------
    url
        the requested url
    data
        the request content
    params
        the query parameters
    headers
        mapping of headers
    method
        the http method
    """
    url:     str
    data:    t.Optional[bytes] = None
    params:  t.Mapping[str, str] = _dictfield()
    headers: Headers = _dictfield()
    method:  str = 'GET'

    def add_headers(self, headers: Headers) -> 'Request':
        """new request with added headers

        Parameters
        ----------
        headers
            the headers to add
        """
        return replace(self, headers={**self.headers, **headers})

    def add_prefix(self, prefix: str) -> 'Request':
        """new request with added url prefix

        Parameters
        ----------
        prefix
            the URL prefix
        """
        return replace(self, url=prefix + self.url)

    def add_params(self, params: t.Mapping[str, str]) -> 'Request':
        """new request with added params

        Parameters
        ----------
        params
            the parameters to add
        """
        return replace(self, params={**self.params, **params})

    def add_basic_auth(self, credentials: t.Tuple[str, str]) -> 'Request':
        """new request with "basic" authentication

        Parameters
        ----------
        credentials
            the username-password pair
        """
        username, password = credentials
        encoded = b64encode(f'{username}:{password}'.encode('ascii'))
        return self.add_headers({
            'Authorization': f'Basic {encoded.decode("ascii")}'})


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


class Sender(abc.ABC):
    """Interface for request senders.
    Any callable which turns a :class:`Request` into a :class:`Response`
    implements it."""

    @abc.abstractmethod
    def __call__(self, request: Request) -> Response:
        raise NotImplementedError()


class AsyncSender(abc.ABC):
    """Interface for ansyncronous request senders.
    Any callable which turns a :class:`Request`
    into an awaitable :class:`Response` implements it.
    """

    @abc.abstractmethod
    def __call__(self, request: Request) -> t.Awaitable[Response]:
        raise NotImplementedError()


def urllib_sender(**kwargs) -> Sender:
    """create a :class:`Sender` using :mod:`urllib`.

    Parameters
    ----------
    **kwargs
        parameters passed to :func:`urllib.request.urlopen`
    """
    def _urllib_send(req: Request) -> Response:
        url = f'{req.url}?{urllib.parse.urlencode(req.params)}'
        raw_request = urllib.request.Request(url, headers=req.headers)
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
    def requests_sender(session: requests.Session) -> Sender:
        """create a :class:`Sender` for a :class:`requests.Session`

        Parameters
        ----------
        session
            a requests session
        """

        def _req_send(req: Request) -> Response:
            response = session.get(req.url, params=req.params,
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
    def aiohttp_sender(session: aiohttp.ClientSession) -> AsyncSender:
        """create a :class:`AsyncSender`
        for a :class:`aiohttp.ClientSession`

        Parameters
        ----------
        session
            a aiohttp session
        """

        async def _aiohttp_sender(req: Request) -> Response:
            async with session.get(req.url,
                                   params=req.params,
                                   data=req.data,
                                   headers=req.headers) as response:
                return Response(
                    response.status,
                    data=await response.text(),
                    headers=response.headers,
                )

        return _aiohttp_sender

    __all__.append('aiohttp_sender')
