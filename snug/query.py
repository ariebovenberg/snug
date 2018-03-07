"""Types and functionality relating to queries"""
import typing as t
from functools import partial

from .clients import send
from .compat import event_loop, func_from_method, urllib_request
from .http import basic_auth

__all__ = [
    'Query',
    'execute',
    'execute_async',
    'executor',
    'async_executor',
    'related',
]

T = t.TypeVar('T')


def _identity(obj):
    return obj


class Query(t.Generic[T]):
    """Abstract base class for query-like objects.
    Any object whose :meth:`~object.__iter__`
    returns a :class:`~snug.http.Request`/:class:`~snug.http.Response`
    generator implements it.

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
    def __iter__(self):
        """A generator iterator which resolves the query

        Returns
        -------
        ~typing.Generator[Request, Response, T]
        """
        raise NotImplementedError()

    def __execute__(self, client, authenticate):
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
        authenticate: ~typing.Callable[[Request], Request]
            a callable to authenticate a :class:`~snug.http.Request`

        Returns
        -------
        T
            the query result
        """
        gen = iter(self)
        request = next(gen)
        while True:
            response = send(client, authenticate(request))
            try:
                request = gen.send(response)
            except StopIteration as e:
                return e.args[0]

    # this method is overwritten when importing the _async module (py3 only)
    def __execute_async__(self, client, authenticate):
        raise NotImplementedError('python 3+ required to execute async')


_default_execute_method = func_from_method(Query.__execute__)


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


def execute(query, auth=None, client=urllib_request.build_opener(),
            auth_method=basic_auth):
    """Execute a query, returning its result

    Parameters
    ----------
    query: Query[T]
        the query to resolve
    auth: T_auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`~snug.clients.send`.
        If not given, the built-in :mod:`urllib` module is used.
    auth_method: ~typing.Callable[[T_auth, Request], Request]
        the authentication method to use

    Returns
    -------
    T
        the query result
    """
    exec_func = getattr(type(query), '__execute__', _default_execute_method)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


def execute_async(query, auth=None, client=event_loop, auth_method=basic_auth):
    """Execute a query asynchronously, returning its result

    Parameters
    ----------
    query: Query[T]
        the query to resolve
    auth: T_auth
        the authentication credentials. If using the default ``auth_method``,
        ``auth`` must be a (username, password)-tuple.
    client
        The HTTP client to use.
        Its type must have been registered
        with :func:`~snug.clients.send_async`.
        If not given, the built-in :mod:`asyncio` module is used.
    auth_method: ~typing.Callable[[T_auth, Request], Request]
        the authentication method to use

    Returns
    -------
    T
        the query result

    Note
    ----
    The default client is very rudimentary.
    Consider using a :class:`aiohttp.ClientSession` instance as ``client``.
    """
    exec_func = getattr(
        type(query), '__execute_async__', Query.__execute_async__)
    authenticate = _identity if auth is None else partial(auth_method, auth)
    return exec_func(query, client, authenticate)


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
