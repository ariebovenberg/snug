"""queries for the 'chat' method family"""
import snug

from .query import json_post
from .types import Message


@json_post('chat.postMessage', rtype=Message, key='message')
def post_message(channel: str, text: str) -> snug.Query[Message]:
    return {'channel': channel, 'text': text}
