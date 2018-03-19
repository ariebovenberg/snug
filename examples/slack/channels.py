"""queries for the 'channels' method family"""
import typing as t

import snug

from .query import paginated_retrieval, json_post
from .types import Channel, Page
from .load import registry

load_channel_list = registry(t.List[Channel])


@paginated_retrieval('channels.list', itemtype=Channel)
def list_(*, cursor: str=None,
          exclude_archived: bool=None,
          exclude_members: bool=None,
          limit: int=None) -> snug.Query[Page[t.List[Channel]]]:
    """list all channels"""
    kwargs = {
        'exclude_archived': exclude_archived,
        'exclude_members':  exclude_members,
        'limit':            limit
    }
    response = yield {'cursor': cursor, **kwargs}
    try:
        next_cursor = response['response_metadata']['next_cursor']
    except KeyError:
        next_query = None
    else:
        next_query = list_(**kwargs, cursor=next_cursor)
    return Page(
        load_channel_list(response['channels']),
        next_query=next_query,
    )


@json_post('channels.create', rtype=Channel, key='channel')
def create(name: str, *,
           validate: bool=None) -> snug.Query[Channel]:
    """create a new channel"""
    return {'name': name, 'validate': validate}
