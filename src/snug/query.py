"""Types and functionality relating to queries"""
import asyncio
import typing as t
import urllib.request
from functools import partial

from .clients import send, send_async
from .http import basic_auth

__all__ = [
    "Query",
    "execute",
    "execute_async",
    "executor",
    "async_executor",
    "related",
]

T = t.TypeVar("T")


def _identity(obj):
    return obj


class Query(t.Generic[T]):
    """Abstract base class for query-like objects.
    Any object whose :meth:`~object.__iter__`
    returns a :class:`~snug.http.Request`/:class:`~snug.http.Response`
    generator implements it.

    Note
    ----
    Generator iterators themselves also implement this interface
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

    def __iter__(self):
        """A generator iterator which resolves the query

        Returns
        -------
        ~typing.Generator[Request, Response, T]
        """
        raise NotImplementedError()

    def __execute__(self, client, auth):
        """Default execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        .. versionadded:: 1.1

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute`
        auth: ~typing.Callable[[Request], Request]
            a callable to authenticate a :class:`~snug.http.Request`

        Returns
        -------
        T
            the query result
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = send(client, auth(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.args[0]

    async def __execute_async__(self, client, auth):
        """Default asynchronous execution logic for a query,
        which uses the query's :meth:`~Query.__iter__`.
        May be overriden for full control of query execution,
        at the cost of reusability.

        .. versionadded:: 1.1

        Note
        ----
        You shouldn't need to override this method, except in rare cases
        where implementing :meth:`Query.__iter__` does not suffice.

        Parameters
        ----------
        client
            the client instance passed to :func:`execute_async`
        auth: ~typing.Callable[[Request], Request]
            a callable to authenticate a :class:`~snug.http.Request`

        Returns
        -------
        T
            the query result
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = await send_async(client, auth(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.value


class related(object):
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
        return self._cls if obj is None else partial(self._cls, obj)


def _make_auth(auth):
    if auth is None:
        return _identity
    elif callable(auth):
        return auth
    else:
        return basic_auth(auth)


def execute(query, auth=None, client=urllib.request.build_opener()):
    """Execute a query, returning its result

    Parameters
    ----------
    query: Query[T]
        The query to resolve
    auth: ~typing.Tuple[str, str] \
        or ~typing.Callable[[Request], Request] or None
        This may be:

        * A (username, password)-tuple for basic authentication
        * A callable to authenticate requests.
        * ``None`` (no authentication)
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`~snug.clients.send`.
        If not given, the built-in :mod:`urllib` module is used.

    Returns
    -------
    T
        the query result
    """
    exec_fn = getattr(type(query), "__execute__", Query.__execute__)
    return exec_fn(query, client, _make_auth(auth))


def execute_async(query, auth=None, client=None):
    """Execute a query asynchronously, returning its result

    Parameters
    ----------
    query: Query[T]
        The query to resolve
    auth: ~typing.Tuple[str, str] \
        or ~typing.Callable[[Request], Request] or None
        This may be:

        * A (username, password)-tuple for basic authentication
        * A callable to authenticate requests.
        * ``None`` (no authentication)
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`~snug.clients.send_async`.
        If not given, the current event loop from :mod:`asyncio` is used.

    Returns
    -------
    T
        the query result

    Note
    ----
    The default client is very rudimentary.
    Consider using a :class:`aiohttp.ClientSession` instance as ``client``.
    """
    exc_fn = getattr(type(query), "__execute_async__", Query.__execute_async__)
    return exc_fn(
        query,
        asyncio.get_event_loop() if client is None else client,
        _make_auth(auth),
    )


def executor(**kwargs):
    """Create a version of :func:`execute` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute`

    Returns
    -------
    ~typing.Callable[[Query[T]], T]
        an :func:`execute`-like function
    """
    return partial(execute, **kwargs)


def async_executor(**kwargs):
    """Create a version of :func:`execute_async` with bound arguments.

    Parameters
    ----------
    **kwargs
        arguments to pass to :func:`execute_async`

    Returns
    -------
    ~typing.Callable[[Query[T]], ~typing.Awaitable[T]]
        an :func:`execute_async`-like function
    """
    return partial(execute_async, **kwargs)
