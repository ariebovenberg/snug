"""Tools for pagination"""
import abc
import typing as t
from operator import attrgetter

from .compat import PY3
from .query import Query, executor

__all__ = [
    'paginated',
    'Page',
    'Pagelike',
]

AsyncIterator = getattr(t, 'AsyncIterator', t.Iterator)
T = t.TypeVar('T')


class Pagelike(t.Generic[T]):
    """ABC for page-like objects.
    Any object implementing the attributes
    :py:attr:`~Pagelike.content` and :py:attr:`~Pagelike.next`
    implements this interface.
    """
    __slots__ = ()

    @abc.abstractproperty
    def content(self):
        """The content of the current page

        Returns
        -------
        T
            The page content
        """
        raise NotImplementedError()

    @abc.abstractproperty
    def next(self):
        """The query to retrieve the next page

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
        The page content
    next: ~snug.Query[Pagelike[T]]] or None
        The query to retrieve the next page
    """
    __slots__ = '_content', '_next'

    def __init__(self, content, next=None):
        self._content, self._next = content, next

    content = property(attrgetter('_content'))
    next = property(attrgetter('_next'))


class paginated(Query[t.Union[t.Iterator[T], AsyncIterator[T]]]):
    """A paginated version of a query

    Parameters
    ----------
    query: Query[Pagelike[T]]
        The query to paginate
    """
    __slots__ = '_query'

    def __init__(self, query):
        self._query = query

    def __execute__(self, client, auth):
        return Paginator(self._query, client, auth)

    def __execute_async__(self, client, auth):
        raise NotImplementedError()


class Paginator(t.Iterator[T]):
    """An iterator which keeps executing the next query in the page sequece"""
    __slots__ = '_execute', '_next_query'

    def __init__(self, query, client, auth):
        self._execute = executor(auth=auth, client=client)
        self._next_query = query

    def __iter__(self):
        return self

    def __next__(self):
        """the content of the next page"""
        if self._next_query is None:
            raise StopIteration()
        page = self._execute(self._next_query)
        self._next_query = page.next
        return page.content

    if not PY3:  # pragma: no cover
        next = __next__

# TODO: AsyncPaginator
