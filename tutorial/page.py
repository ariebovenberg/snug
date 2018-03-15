import abc
import json
import typing as t

import snug


T = t.TypeVar('T')


class Channel:
    ...


class Page(t.Iterable[T]):

    @abc.abstractmethod
    def next(self) -> t.Optional[snug.Query['Page[T]']]:
        raise NotImplementedError()


def list_channels(cursor=None) -> snug.Query[Page[Channel]]:
    """list slack channels"""
    request = snug.GET(f'https://slack.com/api/channels.list',
                       params={'cursor': cursor} if cursor else {})
    response = yield request
    raw_obj = json.loads(response.content)
    next_cursor = raw_obj['response_metadata']['next_cursor']
    return Page(raw_obj['channels'],
                # next_cursor may be None
                next=next_cursor and list_channels(cursor=next_cursor))


class Paginated(snug.Query):

    def __init__(self, initial: snug.Query[Page[T]]):
        self._initial = initial

    def __execute__(self, client, authenticate) -> t.Iterable[T]:
        pass

    def __execute_async__(self, client, authenticate) -> t.AsyncIterable[T]:
        pass


# for page in snug.execute(paginate(list_channels())):
#     ...  # do stuff


# async for page in snug.execute_async(paginate(list_channels())):
#     ...  # do stuff
