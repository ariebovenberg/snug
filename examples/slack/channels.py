"""queries for the 'channels' method family"""
import snug

from .query import paginated_retrieval, json_post
from .types import Channel, Page


@paginated_retrieval('channels.list', itemtype=Channel)
def list(*, cursor: str=None,
         exclude_archived: bool=None,
         exclude_members: bool=None,
         limit: int=None) -> snug.Query[Page[Channel]]:
    """list all channels"""
    return {
        'cursor':           cursor,
        'exclude_archived': exclude_archived,
        'exclude_members':  exclude_members,
        'limit':            limit
    }


@json_post('channels.create', rtype=Channel, key='channel')
def create(name: str, *,
           validate: bool=None) -> snug.Query[Channel]:
    """create a new channel"""
    return {'name': name, 'validate': validate}
