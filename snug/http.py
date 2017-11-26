"""basic HTTP tools"""
import abc
import typing as t
import urllib.request
from base64 import b64encode
from functools import partial

from dataclasses import dataclass, field

from .utils import replace

__all__ = ['Request', 'Response', 'Sender', 'urllib_sender']

_dictfield = partial(field, default_factory=dict)
Headers = t.Mapping[str, str]

T = t.TypeVar('T')
T_parsed = t.TypeVar('T_parsed')


@dataclass(frozen=True)
class Request:
    """a simple HTTP request"""
    url:     str
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


@dataclass(frozen=True)
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
    status_code: int
    content:     bytes
    headers:     Headers


class Sender(abc.ABC):
    """Interface for request senders.
    Any callable which turns a :class:`Request` into a :class:`Response`
    implements it."""

    @abc.abstractmethod
    def __call__(self, request: Request) -> Response:
        raise NotImplementedError()


def urllib_sender(**kwargs) -> Sender:
    """create a :class:`Sender` callable using :mod:`urllib`.

    Parameters
    ----------
    **kwargs
        parameters passed to :meth:`urllib.request.urlopen`
    """
    def _urllib_send(req: Request) -> Response:
        url = f'{req.url}?{urllib.parse.urlencode(req.params)}'
        raw_request = urllib.request.Request(url, headers=req.headers)
        raw_response = urllib.request.urlopen(raw_request, **kwargs)
        return Response(
            raw_response.getcode(),
            content=raw_response.read(),
            headers=raw_response.headers,
        )

    return _urllib_send


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    def requests_sender(session: requests.Session) -> Sender:
        """create a :class:`Sender` for a :class:`requests.Session`"""

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
