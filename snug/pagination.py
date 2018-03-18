"""Tools for pagination"""
import abc
import sys
import typing as t
from operator import attrgetter
from functools import partial

from .compat import PY3
from .query import Query, executor, async_executor

__all__ = [
    'paginated',
    'Page',
    'Pagelike',
]

AsyncIterator = getattr(t, 'AsyncIterator', t.Iterator)
T = t.TypeVar('T')


class Pagelike(t.Generic[T]):
    """Abstract base class for page-like objects.
    Any object implementing the attributes
    :py:attr:`~Pagelike.content` and :py:attr:`~Pagelike.next`
    implements this interface.
    """
    __slots__ = ()

    @abc.abstractproperty
    def content(self):
        """The contents of the page

        Returns
        -------
        T
            The page content.
        """
        raise NotImplementedError()

    @abc.abstractproperty
    def next(self):
        """The query to retrieve the next page,
        or ``None`` if there is no next page.

        Returns
        -------
        ~snug.Query[Pagelike[T]]] or None
            The next query
        """
        raise NotImplementedError()


class Page(Pagelike[T]):
    """A simple :class:`Pagelike` object

    Parameters
    ----------
    content: T
        The page content.
    next: ~snug.Query[Pagelike[T]]] or None
        The query to retrieve the next page
    """
    __slots__ = '_content', '_next'

    def __init__(self, content, next=None):
        self._content, self._next = content, next

    content = property(attrgetter('_content'))
    next = property(attrgetter('_next'))


class paginated(Query[t.Union[t.Iterator[T], AsyncIterator[T]]]):
    """A paginated version of a query.
    Executing it returns an :term:`iterator`
    or :term:`async iterator <asynchronous iterator>`.

    Parameters
    ----------
    query: Query[Pagelike[T]]
        The query to paginate.
        This query must return a :class:`Pagelike` object.

    Note
    ----
    Async iterators were introduced in
    `PEP 492 <https://www.python.org/dev/peps/pep-0492>`_.
    Therefore, async execution of :class:`paginated`
    queries is only supported on python 3.5.2+.

    Example
    -------

    .. code-block:: python

        def foo_page(...) -> Query[Pagelike[Foo]]  # example query
            ...

        query = paginated(foo_page(...))

        for foo in execute(query):
            ...

        async for foo in execute_async(query):  # python 3.5.2+ only
            ...
    """
    __slots__ = '_query'

    def __init__(self, query):
        self._query = query

    def __execute__(self, client, auth):
        return Paginator(self._query, executor(client=client, auth=auth))

    def __execute_async__(self, client, auth):
        raise NotImplementedError(
            'async execution of paginated queries is python 3.5.2+ only')


class Paginator(t.Iterator[T]):
    """An iterator which keeps executing the next query in the page sequece"""
    __slots__ = '_executor', '_next_query'

    def __init__(self, next_query, executor):
        self._next_query, self._executor = next_query, executor

    def __iter__(self):
        return self

    def __next__(self):
        """the content of the next page"""
        if self._next_query is None:
            raise StopIteration()
        page = self._executor(self._next_query)
        self._next_query = page.next
        return page.content

    if not PY3:  # pragma: no cover
        next = __next__


if sys.version_info > (3, 5, 2):
    from ._async import AsyncPaginator

    @partial(setattr, paginated, '__execute_async__')
    def __execute_async__(self, client, auth):
        return AsyncPaginator(self._query,
                              async_executor(client=client, auth=auth))
