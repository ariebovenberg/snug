"""Basic HTTP abstractions and functionality"""
from base64 import b64encode
from collections import OrderedDict
from functools import partial
from itertools import chain
from operator import methodcaller

__all__ = [
    'Request',
    'Response',
    'header_adder',
    'prefix_adder',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
]


class _SlotsMixin(object):
    __slots__ = ()

    def _asdict(self):
        return OrderedDict((a, getattr(self, a)) for a in self.__slots__)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._asdict() == other._asdict()
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self._asdict() != other._asdict()
        return NotImplemented

    def replace(self, **kwargs):
        """Create a copy with replaced fields

        Parameters
        ----------
        **kwargs
            fields and values to replace
        """
        merged = dict(chain(self._asdict().items(), kwargs.items()))
        return self.__class__(**merged)


class Request(_SlotsMixin):
    """A simple HTTP request.

    Parameters
    ----------
    method: str
        The http method
    url: str
        The requested url
    content: bytes or None
        The request content
    params: Mapping
        The query parameters. Defaults to an empty :class:`dict`.
    headers: Mapping
        Request headers. Defaults to an empty :class:`dict`.
    """
    __slots__ = 'method', 'url', 'content', 'params', 'headers'
    __hash__ = None

    def __init__(self, method, url, content=None, params=None, headers=None):
        self.method = method
        self.url = url
        self.content = content
        self.params = {} if params is None else params
        self.headers = {} if headers is None else headers

    def with_headers(self, headers):
        """Create a new request with added headers

        Parameters
        ----------
        headers: Mapping
            the headers to add
        """
        merged = self.headers.copy()
        merged.update(headers)
        return self.replace(headers=merged)

    def with_prefix(self, prefix):
        """Create a new request with added url prefix

        Parameters
        ----------
        prefix: str
            the URL prefix
        """
        return self.replace(url=prefix + self.url)

    def with_params(self, params):
        """Create a new request with added query parameters

        Parameters
        ----------
        params: Mapping
            the query parameters to add
        """
        merged = self.params.copy()
        merged.update(params)
        return self.replace(params=merged)

    def __repr__(self):
        return ('<Request: {0.method} {0.url}, params={0.params!r}, '
                'headers={0.headers!r}>').format(self)


class Response(_SlotsMixin):
    """A simple HTTP response.

    Parameters
    ----------
    status_code: int
        The HTTP status code
    content: bytes or None
        The response content
    headers: Mapping
        The headers of the response. Defaults to an empty :class:`dict`.
    """
    __slots__ = 'status_code', 'content', 'headers'
    __hash__ = None

    def __init__(self, status_code, content=None, headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers

    def __repr__(self):
        return ('<Response: {0.status_code}, '
                'headers={0.headers!r}>').format(self)


def basic_auth(credentials, request):
    """Apply basic authentication to a request"""
    encoded = b64encode(':'.join(credentials).encode('ascii')).decode()
    return request.with_headers({'Authorization': 'Basic ' + encoded})


prefix_adder = partial(methodcaller, 'with_prefix')
prefix_adder.__doc__ = "make a callable which adds a prefix to a request url"
header_adder = partial(methodcaller, 'with_headers')
header_adder.__doc__ = "make a callable which adds headers to a request"
GET = partial(Request, 'GET')
GET.__doc__ = "shortcut for a GET request"
POST = partial(Request, 'POST')
POST.__doc__ = "shortcut for a POST request"
PUT = partial(Request, 'PUT')
PUT.__doc__ = "shortcut for a PUT request"
PATCH = partial(Request, 'PATCH')
PATCH.__doc__ = "shortcut for a PATCH request"
DELETE = partial(Request, 'DELETE')
DELETE.__doc__ = "shortcut for a DELETE request"
HEAD = partial(Request, 'HEAD')
HEAD.__doc__ = "shortcut for a HEAD request"
OPTIONS = partial(Request, 'OPTIONS')
OPTIONS.__doc__ = "shortcut for a OPTIONS request"
