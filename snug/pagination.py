"""Tools for pagination"""
import abc
import typing as t

from .query import Query

__all__ = [
    # 'Pagelike',
    'Page',
    'paginate',
]


T = t.TypeVar('T')


# class Pagelike(t.Generic[T]):
#     """ABC for page-like objects"""

#     @abc.abstractproperty
#     def next(self):
#         """The next query in page sequence

#         Returns
#         -------
#         ~snug.Query[Pagelike[T]]] or None
#             The query
#         """
#         raise NotImplementedError()


# class Page(Pagelike[T]):
class Page(t.Generic[T]):
    """A simple, concrete :class:`Pagelike` object

    Parameters
    ----------
    content: T
        content of the page
    next: ~snug.Query[Pagelike[T]]] or None
        the next page
    """
    def __init__(self, content, next):
        self.content, self.next = content, next


class paginate(Query):
    """Create a paginator over this query

    Parameters
    ----------
    query: Query[T]

    Returns
    -------
    Query[Paginator[T]]
        A query returning a paginator
    """
    def __init__(self, query):
        self._query = query

    def __execute__(self, client, auth):
        import pdb; pdb.set_trace()

    def __execute_async(self, client, auth):
        raise NotImplementedError


class Paginator(t.Iterator[T]):

    def __init__(self):
        pass

    def __next__(self):
        """the content of the next page"""
        


class AsyncPaginator(t.AsyncIterator[T]):
    """TODO: implement"""


# def list_channels(cursor=None) -> snug.Query[Page[Channel]]:
#     """list slack channels"""
#     request = snug.GET(f'https://slack.com/api/channels.list',
#                        params={'cursor': cursor} if cursor else {})
#     response = yield request
#     raw_obj = json.loads(response.content)
#     next_cursor = raw_obj['response_metadata']['next_cursor']
#     return Page(raw_obj['channels'],
#                 # next_cursor may be None
#                 next=next_cursor and list_channels(cursor=next_cursor))


# class Paginated(snug.Query):

#     def __init__(self, initial: snug.Query[Page[T]]):
#         self._initial = initial

#     def __execute__(self, client, authenticate) -> t.Iterable[T]:
#         pass

#     def __execute_async__(self, client, authenticate) -> t.AsyncIterable[T]:
#         pass


# # for page in snug.execute(paginate(list_channels())):
# #     ...  # do stuff


# # async for page in snug.execute_async(paginate(list_channels())):
# #     ...  # do stuff
