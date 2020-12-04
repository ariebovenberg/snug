"""Tools for creating paginated queries

.. versionadded:: 1.2
"""
import abc
import typing as t
from operator import attrgetter

from .query import Query, async_executor, executor

__all__ = ["paginated", "Page", "Pagelike"]

T = t.TypeVar("T")


class Pagelike(t.Generic[T]):
    """Abstract base class for page-like objects.
    Any object implementing the attributes
    :py:attr:`~Pagelike.content` and :py:attr:`~Pagelike.next_query`
    implements this interface.
    A query returning such an object may be :class:`paginated`.

    Note
    ----
    Pagelike is a :class:`~typing.Generic`.
    This means you may write ``Pagelike[<type-of-content>]``
    as a descriptive type annotation.

    For example: ``Pagelike[List[str]]`` indicates a page-like
    object whose ``content`` is a list of strings.
    """

    __slots__ = ()

    @abc.abstractproperty
    def content(self):
        """The contents of the page.

        Returns
        -------
        T
            The page content.
        """
        raise NotImplementedError()

    @abc.abstractproperty
    def next_query(self):
        """The query to retrieve the next page,
        or ``None`` if there is no next page.

        Returns
        -------
        ~snug.Query[Pagelike[T]]] or None
            The next query.
        """
        raise NotImplementedError()


class Page(Pagelike[T]):
    """A simple :class:`Pagelike` object

    Parameters
    ----------
    content: T
        The page content.
    next_query: ~snug.Query[Pagelike[T]]] or None
        The query to retrieve the next page.
    """

    __slots__ = "_content", "_next_query"

    def __init__(self, content, next_query=None):
        self._content, self._next_query = content, next_query

    content = property(attrgetter("_content"))
    next_query = property(attrgetter("_next_query"))

    def __repr__(self):
        return "Page({})".format(self._content)


class paginated(Query[t.Union[t.Iterator[T], t.AsyncIterator[T]]]):
    """A paginated version of a query.
    Executing it returns an :term:`iterator`
    or :term:`async iterator <asynchronous iterator>`.

    If the wrapped query is reusable,
    the paginated query is also reusable.

    Parameters
    ----------
    query: Query[Pagelike[T]]
        The query to paginate.
        This query must return a :class:`Pagelike` object.

    Example
    -------

    .. code-block:: python

        def foo_page(...) -> Query[Pagelike[Foo]]  # example query
            ...
            return Page(...)

        query = paginated(foo_page(...))

        for foo in execute(query):
            ...

        async for foo in execute_async(query):
            ...
    """

    __slots__ = "_query"

    def __init__(self, query):
        self._query = query

    def __execute__(self, client, auth):
        """Execute the paginated query.

        Returns
        -------
        ~typing.Iterator[T]
            An iterator yielding page content.
        """
        return Paginator(self._query, executor(client=client, auth=auth))

    def __execute_async__(self, client, auth):
        """Execute the paginated query asynchronously.

        Note
        ----
        This method does not need to be awaited.

        Returns
        -------
        ~typing.AsyncIterator[T]
            An asynchronous iterator yielding page content.
        """
        return AsyncPaginator(
            self._query, async_executor(client=client, auth=auth)
        )

    def __repr__(self):
        return "paginated({})".format(self._query)


class Paginator(t.Iterator[T]):
    """An iterator which keeps executing the next query in the page sequece,
    returning the page content."""

    __slots__ = "_executor", "_next_query"

    def __init__(self, next_query, executor):
        self._next_query, self._executor = next_query, executor

    def __iter__(self):
        return self

    def __next__(self):
        if self._next_query is None:
            raise StopIteration()
        page = self._executor(self._next_query)
        self._next_query = page.next_query
        return page.content


class AsyncPaginator(t.AsyncIterator[T]):
    """An async iterator which keeps executing
    the next query in the page sequence"""

    __slots__ = "_executor", "_next_query"

    def __init__(self, next_query, executor):
        self._next_query, self._executor = next_query, executor

    def __aiter__(self):
        return self

    async def __anext__(self):
        """the content of the next page"""
        if self._next_query is None:
            raise StopAsyncIteration()
        page = await self._executor(self._next_query)
        self._next_query = page.next_query
        return page.content
