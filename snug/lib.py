"""library of miscelaneous helpers"""
import abc
import json
import typing as t
from dataclasses import replace
from functools import partial

from . import pipe as _pipe
from . import asnc, http, sender
from .core import Query, Sender, T_req, T_resp, exec
from .utils import JSONType, flip, oneyield

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')


class Authenticator(t.Generic[T_auth]):
    """interface for authenticator callables"""

    @abc.abstractmethod
    def __call__(self, request: T_req, auth: T_auth) -> T_req:
        raise NotImplementedError()


def jsonpipe(request: http.Request) -> t.Generator[http.Request,
                                                   http.Response,
                                                   JSONType]:
    """a simple pipe for requests with JSON content"""
    prepared = (replace(request, data=json.dumps(request.data).encode('ascii'))
                if request.data else request)
    response = yield prepared
    return json.loads(response.data) if response.data else None


Resolver = t.Callable[[Query[T_req, T_resp, T]], T]
"""interface for query resolvers"""

AsyncResolver = t.Callable[[Query[T_req, T_resp, T]], t.Awaitable[T]]
"""interface for asynchronous resolvers"""


def build_resolver(
        auth:          T_auth,
        send:          Sender,
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
    piped = sender.Piped(_pipe.Chain(
        pipe,
        oneyield(partial(flip(authenticator), auth)),
    ), send)
    return partial(exec, piped)


def build_async_resolver(
        auth:          T_auth,
        send:          asnc.Sender,
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
    piped = asnc.PipedSender(_pipe.Chain(
        pipe,
        oneyield(partial(flip(authenticator), auth)),
    ), send)
    return partial(asnc.exec, piped)


basic_resolver = partial(exec, http.urllib_sender())
