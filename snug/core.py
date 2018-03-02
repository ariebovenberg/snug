import asyncio
import sys
import typing as t
import urllib.request
from functools import partial
from types import MethodType

from .clients import send, send_async
from .http import Request, Response, basic_auth

__all__ = [
    'Query',
    'execute',
    'execute_async',
    'executor',
    'async_executor',
    'related',
]

T = t.TypeVar('T')
T_auth = t.TypeVar('T_auth')
_Awaitable = (t.Awaitable.__getitem__  # pragma: no cover
              if sys.version_info > (3, 5)
              else lambda x: t.Generator[t.Any, t.Any, x])
_Executor = t.Callable[['Query[T]'], T]
_AExecutor = t.Callable[['Query[T]'], _Awaitable(T)]
_AuthMethod = t.Callable[[T_auth, 'Request'], 'Request']


def _identity(obj):
    return obj


class Query(t.Generic[T], t.Iterable[Request]):
    """Abstract base class for query-like objects.
    Any object whose :meth:`~object.__iter__`
    returns a :class:`Request`/:class:`Response` generator implements it.

    Note
    ----
    :term:`Generator iterator`\\s themselves also implement this interface
    (i.e. :meth:`~object.__iter__` returns the generator itself).

    Note
    ----
    Query is a :class:`~typing.Generic`.
    This means you may write ``Query[<returntype>]``
    as a descriptive type annotation.

    For example: ``Query[bool]`` indicates a query which returns a boolean.

    Examples
    --------

    Creating a query from a generator function:

    >>> def repo(name: str, owner: str) -> snug.Query[dict]:
    ...    \"\"\"a repo lookup by owner and name\"\"\"
    ...    req = snug.GET(f'https://api.github.com/repos/{owner}/{name}')
    ...    response = yield req
    ...    return json.loads(response.content)
    ...
    >>> query = repo('Hello-World', owner='octocat')

    Creating a class-based query:

    >>> # actually subclassing `Query` is not required
    >>> class repo(snug.Query[dict]):
    ...    \"\"\"a repository lookup by owner and name\"\"\"
    ...    def __init__(self, name: str, owner: str):
    ...        self.name, self.owner = name, owner
    ...
    ...    def __iter__(self):
    ...        owner, name = self.owner, self.name
    ...        request = snug.GET(
    ...            f'https://api.github.com/repos/{owner}/{name}')
    ...        response = yield request
    ...        return json.loads(response.content)
    ...
    >>> query = repo('Hello-World', owner='octocat')

    Creating a fully customized query (for rare cases):

    >>> # actually subclassing `Query` is not required
    >>> class asset_download(snug.Query):
    ...     \"\"\"streaming download of a repository asset.
    ...     Can only be executed with particular clients\"\"\"
    ...     def __init__(self, repo_name, repo_owner, id):
    ...         self.request = snug.GET(
    ...             f'https://api.github.com/repos/{repo_owner}'
    ...             f'/{repo_name}/releases/assets/{id}',
    ...             headers={'Accept': 'application/octet-stream'})
    ...
    ...     def __execute__(self, client, authenticate):
    ...         \"\"\"execute, returning a streaming requests response\"\"\"
    ...         assert isinstance(client, requests.Session)
    ...         req = authenticate(self.request)
    ...         return client.request(req.method, req.url,
    ...                               data=req.content,
    ...                               params=req.params,
    ...                               headers=req.headers,
    ...                               stream=True)
    ...
    ...     async def __execute_async__(self, client, authenticate):
    ...         ...
    ...
    >>> query = asset_download('hub', rep_owner='github', id=4187895)
    >>> response = snug.execute(download, client=requests.Session())
    >>> for chunk in response.iter_content():
    ...    ...
    """
    def __iter__(self) -> t.Generator[Request, Response, T]:
        """A generator iterator which resolves the query"""
        raise NotImplementedError()

    def __execute__(self, client,
                    authenticate: t.Callable[[Request], Request]) -> T:
        """Default execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute`
        authenticate
            a callable to authenticate a :class:`Request`
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = send(client, authenticate(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value

    @asyncio.coroutine
    def __execute_async__(self, client,
                          authenticate: t.Callable[[Request], Request]) -> T:
        """Default asynchronous execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute`
        authenticate
            a callable to authenticate a :class:`Request`
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = yield from send_async(client, authenticate(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value


class related:
    """Decorate classes to make them callable as methods.
    This can be used to implement related queries
    through nested classes.

    Example
    -------

    >>> class Foo:
    ...     @related
    ...     class Bar:
    ...         def __init__(self, foo, qux):
    ...             self.the_foo, self.qux = foo, qux
    ...
    >>> f = Foo()
    >>> b = p.Bar(qux=5)
    >>> isinstance(b, Foo.Bar)
    True
    >>> b.the_foo is f
    True
    """
    def __init__(self, cls):
        self._cls = cls

    def __get__(self, obj, objtype=None):
        return self._cls if obj is None else MethodType(self._cls, obj)


def execute(query: Query[T], *,
            auth: T_auth=None,
            client=urllib.request.build_opener(),
            auth_method: _AuthMethod=basic_auth) -> T:
    """Execute a query, returning its result

    Parameters
    ----------
    query
        the query to resolve
    auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`send`.
        If not given, the built-in :mod:`urllib` module is used.
    auth_method
        the authentication method to use
    """
    exec_func = getattr(type(query), '__execute__', Query.__execute__)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


def execute_async(query: Query[T], *,
                  auth: T_auth=None,
                  client=asyncio.get_event_loop(),
                  auth_method: _AuthMethod=basic_auth) -> _Awaitable(T):
    """Execute a query asynchronously, returning its result

    Parameters
    ----------
    query
        the query to resolve
    auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`send_async`.
        If not given, the built-in :mod:`asyncio` module is used.
    auth_method
        the authentication method to use

    Note
    ----
    The default client is very rudimentary.
    Consider using a :class:`aiohttp.ClientSession` instance as ``client``.
    """
    exec_func = getattr(
        type(query), '__execute_async__', Query.__execute_async__)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


def executor(**kwargs) -> _Executor:
    """Create a version of :func:`execute` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute`
    """
    return partial(execute, **kwargs)


def async_executor(**kwargs) -> _AExecutor:
    """Create a version of :func:`execute_async` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute_async`
    """
    return partial(execute_async, **kwargs)
