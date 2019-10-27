"""Basic HTTP abstractions and functionality"""
from base64 import b64encode
from collections.abc import Mapping
from functools import partial
from itertools import chain
from operator import attrgetter, methodcaller

__all__ = [
    "Request",
    "Response",
    "header_adder",
    "prefix_adder",
    "basic_auth",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
]


class _FrozenDict(Mapping):
    __slots__ = "_inner"

    def __init__(self, inner=()):
        self._inner = dict(inner)

    __len__ = property(attrgetter("_inner.__len__"))
    __iter__ = property(attrgetter("_inner.__iter__"))
    __getitem__ = property(attrgetter("_inner.__getitem__"))
    __repr__ = property(attrgetter("_inner.__repr__"))


class _SlotsMixin(object):
    __slots__ = ()

    def _asdict(self):
        return {a: getattr(self, a) for a in self.__slots__}

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
        return type(self)(**_merge_maps(self._asdict(), kwargs))


def _merge_maps(m1, m2):
    """merge two Mapping objects, keeping the type of the first mapping"""
    return type(m1)(chain(m1.items(), m2.items()))


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
        The query parameters.
    headers: Mapping
        Request headers.
    """

    __slots__ = "method", "url", "content", "params", "headers"
    __hash__ = None

    def __init__(
        self,
        method,
        url,
        content=None,
        params=_FrozenDict(),
        headers=_FrozenDict(),
    ):
        self.method = method
        self.url = url
        self.content = content
        self.params = params
        self.headers = headers

    def with_headers(self, headers):
        """Create a new request with added headers

        Parameters
        ----------
        headers: Mapping
            the headers to add
        """
        return self.replace(headers=_merge_maps(self.headers, headers))

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
        return self.replace(params=_merge_maps(self.params, params))

    def __repr__(self):
        return (
            "<Request: {0.method} {0.url}, params={0.params!r}, "
            "headers={0.headers!r}>"
        ).format(self)


class Response(_SlotsMixin):
    """A simple HTTP response.

    Parameters
    ----------
    status_code: int
        The HTTP status code
    content: bytes or None
        The response content
    headers: Mapping
        The headers of the response.
    """

    __slots__ = "status_code", "content", "headers"
    __hash__ = None

    def __init__(self, status_code, content=None, headers=_FrozenDict()):
        self.status_code = status_code
        self.content = content
        self.headers = headers

    def __repr__(self):
        return (
            "<Response: {0.status_code}, " "headers={0.headers!r}>"
        ).format(self)


def basic_auth(credentials):
    """Create an HTTP basic authentication callable

    Parameters
    ----------
    credentials: ~typing.Tuple[str, str]
        The (username, password)-tuple

    Returns
    -------
    ~typing.Callable[[Request], Request]
        A callable which adds basic authentication to a :class:`Request`.
    """
    encoded = b64encode(":".join(credentials).encode("ascii")).decode()
    return header_adder({"Authorization": "Basic " + encoded})


prefix_adder = partial(methodcaller, "with_prefix")
prefix_adder.__doc__ = """
Make a callable which adds a prefix to a request url

Example
-------

>>> func = snug.prefix_adder('https://api.test.com/v1/')
>>> func(snug.GET('foo/bar/')).url
https://api.test.com/v1/foo/bar/
"""
header_adder = partial(methodcaller, "with_headers")
header_adder.__doc__ = """
Make a callable which adds headers to a request

Example
-------

>>> func = snug.header_adder({'content-type': 'application/json'})
>>> func(snug.GET('https://test.dev')).headers
{'content-type': 'application/json'}
"""
GET = partial(Request, "GET")
GET.__doc__ = "Shortcut for a GET request"
POST = partial(Request, "POST")
POST.__doc__ = "Shortcut for a POST request"
PUT = partial(Request, "PUT")
PUT.__doc__ = "Shortcut for a PUT request"
PATCH = partial(Request, "PATCH")
PATCH.__doc__ = "Shortcut for a PATCH request"
DELETE = partial(Request, "DELETE")
DELETE.__doc__ = "shortcut for a DELETE request"
HEAD = partial(Request, "HEAD")
HEAD.__doc__ = "Shortcut for a HEAD request"
OPTIONS = partial(Request, "OPTIONS")
OPTIONS.__doc__ = "Shortcut for a OPTIONS request"
