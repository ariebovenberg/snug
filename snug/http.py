"""basic HTTP tools"""
import typing as t
from base64 import b64encode
from functools import partial, singledispatch

import requests
from dataclasses import dataclass, field

from .utils import replace

_dictfield = partial(field, default_factory=dict)
Headers = t.Mapping[str, str]


@dataclass(frozen=True)
class Request:
    """a simple HTTP request"""
    url:     str
    params:  t.Mapping[str, str] = _dictfield()
    headers: Headers = _dictfield()
    method:  str = 'GET'

    def add_headers(self, headers: Headers) -> 'Request':
        """new request with added headers"""
        return replace(self, headers={**self.headers, **headers})

    def add_prefix(self, prefix: str) -> 'Request':
        """new request with added url prefix"""
        return replace(self, url=prefix + self.url)

    def add_params(self, params: t.Mapping[str, str]) -> 'Request':
        """new request with added params"""
        return replace(self, params={**self.params, **params})

    def add_basic_auth(self, username: str, password: str):
        """new request with "basic" authentication"""
        encoded = b64encode(f'{username}:{password}'.encode('ascii'))
        return self.add_headers({
            'Authorization': f'Basic {encoded.decode("ascii")}'})


@dataclass(frozen=True)
class Response:
    """a simple HTTP response"""
    status_code: int
    content:     bytes
    headers:     Headers


@singledispatch
def send(client, request: Request) -> Response:
    """send an HTTP request, returning a Response"""
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
