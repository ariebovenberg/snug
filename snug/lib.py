"""library of miscelaneous helpers"""
import abc
import typing as t
import json
from dataclasses import replace
from functools import partial

from .abc import resolve, Query, Sender, T_req, T_resp
from . import http, pipe as _pipe, asyn, sender
from .utils import JSONType, flip


T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')


class Authenticator(t.Generic[T_auth]):
    """interface for authenticator callables"""

    @abc.abstractmethod
    def __call__(self, request: T_req, auth: T_auth) -> T_req:
        raise NotImplementedError()


def jsonpipe(request: http.Request[t.Optional[bytes]]) -> t.Generator[
        http.Request[JSONType], http.Response[t.Optional[bytes]], JSONType]:
    """a simple pipe for requests with JSON content"""
    prepared = (replace(request, data=json.dumps(request.data).encode('ascii'))
                if request.data else request)
    response = yield prepared
    return json.loads(response.data) if response.data else None


Resolver = t.Callable[[Query[T, T_req, T_resp]], T]
"""interface for query resolvers"""

AsyncResolver = t.Callable[[Query[T, T_req, T_resp]], t.Awaitable[T]]
"""interface for asynchronous resolvers"""


def build_resolver(
        auth:          T_auth,
        send:        Sender,
        authenticator: Authenticator[T_auth],
        pipe:          _pipe.Pipe=_pipe.identity) -> Resolver:
    """create an authenticated resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    pipe
        pipe to apply to all requests
    """
    piped = sender.Piped(send, _pipe.Chain(
        pipe,
        _pipe.Preparer(partial(flip(authenticator), auth)),
    ))
    return partial(resolve, piped)


def build_async_resolver(
        auth:          T_auth,
        send:        asyn.Sender,
        authenticator: Authenticator[T_auth],
        pipe:          _pipe.Pipe=_pipe.identity) -> AsyncResolver:
    """create an authenticated, asynchronous, resolver

    Parameters
    ----------
    auth
        authentication information
    sender
        the request sender
    authenticator
        authenticator function
    pipe
        pipe to apply to all requests
    """
    piped = asyn.PipedSender(send, _pipe.Chain(
        pipe,
        _pipe.Preparer(partial(flip(authenticator), auth)),
    ))
    return partial(asyn.resolve, piped)


simple_resolver = partial(
    build_resolver,
    send=http.urllib_sender(),
    authenticator=lambda r, auth: (r if auth is None
                                   else r.add_basic_auth(auth)),
    pipe=jsonpipe,
)
