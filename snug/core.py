"""the central abstractions"""
import abc
import typing as t
import urllib.request
from base64 import b64encode
from functools import partial, singledispatch
from itertools import chain
from operator import methodcaller

from .utils import EMPTY_MAPPING, compose, identity

__all__ = [
    'Request',
    'Response',
    'Query',
    'executor',
    'urllib_sender',
    'sender',
    'header_adder',
    'prefix_adder',
    'execute',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
]

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')


class Request:
    """a simple HTTP request

    Parameters
    ----------
    method: str
        the http method
    url: str
        the requested url
    data: ~typing.Optional[bytes]
        the request content
    params: ~typing.Mapping[str, str]
        the query parameters
    headers: ~typing.Mapping[str, str]
        mapping of headers
    """
    __slots__ = 'method', 'url', 'data', 'params', 'headers'
    __hash__ = None

    def __init__(self, method, url, data=None, params=EMPTY_MAPPING,
                 headers=EMPTY_MAPPING):
        self.method = method
        self.url = url
        self.data = data
        self.params = params
        self.headers = headers

    def with_headers(self, headers):
        """new request with added headers

        Parameters
        ----------
        headers: ~typing.Mappping[str, str]
            the headers to add

        Returns
        -------
        Request
            a new request with added headers
        """
        return self.replace(headers=dict(chain(self.headers.items(),
                                               headers.items())))

    def with_prefix(self, prefix):
        """new request with added url prefix

        Parameters
        ----------
        prefix: str
            the URL prefix

        Returns
        -------
        Request
            a new request with added prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params):
        """new request with added params

        Parameters
        ----------
        params: ~typing.Mapping[str, str]
            the parameters to add

        Returns
        -------
        Request
            a new request with added parameters
        """
        return self.replace(params=dict(chain(self.params.items(),
                                              params.items())))

    def with_basic_auth(self, credentials):
        """new request with "basic" authentication

        Parameters
        ----------
        credentials: ~typing.Tuple[str, str]
            the username-password pair

        Returns
        -------
        Request
            a new request with added authentication
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
        """create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace

        Returns
        -------
        Request
            the new request
        """
        attrs = self._asdict()
        attrs.update(kwargs)
        return Request(**attrs)

    def __repr__(self):
        return ('<Request: {0.method} {0.url}, params={0.params!r}, '
                'headers={0.headers!r}>').format(self)


class Response:
    """a simple HTTP response

    Parameters
    ----------
    status_code: int
        the HTTP status code
    data: ~typing.Optional[bytes]
        the response content
    headers: ~typing.Mapping[str, str]
        the headers of the response
    """
    __slots__ = 'status_code', 'data', 'headers'
    __hash__ = None

    def __init__(self, status_code, data=None, headers=EMPTY_MAPPING):
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
        attrs = self._asdict()
        attrs.update(kwargs)
        return Response(**attrs)


class Query(t.Generic[T], t.Iterable[Request]):
    """ABC for query-like objects.
    Any object where ``__iter__`` returns a generator implements it"""

    @abc.abstractmethod
    def __iter__(self):
        """resolve the query

        Returns
        -------
        ~typing.Generator[Request, Response, T]
            a generator which resolves the query
        """
        raise NotImplementedError()


def urllib_sender(req, **kwargs):
    """simple sender which uses python's :mod:`urllib`

    Parameters
    ----------
    req: Request
        the request to send
    **kwargs
        keywords to use

    Returns
    -------
    Response
        the resulting response
    """
    url = req.url + '?' + urllib.parse.urlencode(req.params)
    raw_request = urllib.request.Request(url, headers=req.headers,
                                         method=req.method)
    raw_response = urllib.request.urlopen(raw_request, **kwargs)
    return Response(
        raw_response.getcode(),
        data=raw_response.read(),
        headers=raw_response.headers,
    )


def _optional_basic_auth(credentials):
    """create an authenticator for optional credentials

    Parameters
    ----------
    credentials: ~typing.Optional[~typing.Tuple[str, str]]
        the username and password

    Returns
    -------
    ~typing.Callable[[Request], Request]
        a request authenticator

    """
    if credentials is None:
        return identity
    else:
        return methodcaller('with_basic_auth', credentials)


def executor(auth=None,
             client=None,
             authenticator=_optional_basic_auth):
    """create an executor

    Parameters
    ----------
    auth: T_credentials
        the credentials
    client
        The HTTP client to use.
    authenticator: Authenticator[T_credentials]
        the authentication method to use

    Returns
    -------
    Executor
        an executor
    """
    _sender = urllib_sender if client is None else sender(client)
    return partial(execute, sender=compose(_sender, authenticator(auth)))


@singledispatch
def sender(client):
    """create a sender for the given client

    Parameters
    ----------
    client: any registered client type
        the HTTP client to create a sender from

    Returns
    -------
    Sender
        a request sender
    """
    raise TypeError('no sender factory registered for {!r}'.format(client))


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @sender.register(requests.Session)
    def _requests_sender(session: requests.Session):
        """create a :class:`~snug.Sender` for a :class:`requests.Session`

        Parameters
        ----------
        session
            a requests session

        Returns
        -------
        Sender
            a request sender
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


def execute(query, sender=urllib_sender):
    """execute a query

    Parameters
    ----------
    query: Query[T_return]
        the query to resolve
    sender: ~typing.Callable[[Request], Response]
        the sender to use

    Returns
    -------
    T_return
        the query return value
    """
    gen = iter(query)
    request = next(gen)
    while True:
        response = sender(request)
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value
