"""basic HTTP tools"""
import typing as t
from base64 import b64encode
from functools import partial, singledispatch

import requests
from dataclasses import dataclass, field

from .utils import replace

__all__ = ['Request', 'Response', 'send']

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
class Response(t.Generic[T]):
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
    content:     T
    headers:     Headers

    def __getitem__(self, key):
        return self.content[key]

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        return iter(self.content)

    def parse_content(self, func: t.Callable[[T], T_parsed]) -> (
            'Response[T_parsed]'):
        return replace(self, content=func(self.content))


@singledispatch
def send(client, request: Request) -> Response:
    """send an HTTP request, returning a Response

    This is a :func:`~functools.singledispatch` function:
    different types of HTTP clients can be supported by registering them.

    Parameters
    ----------
    client
        the HTTP client
    request
        the request to send
    """
    raise TypeError(client)


@send.register(requests.Session)
def _send_with_requests_session(client, request):
    assert request.method == 'GET', 'only GET implemented for now'
    response = client.get(request.url,
                          headers=request.headers,
                          params=request.params)
    response.raise_for_status()
    return Response(status_code=response.status_code,
                    content=response.content,
                    headers=response.headers)
