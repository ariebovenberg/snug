"""wrapper for the github API"""
import snug

from .types import *  # noqa
from . import channels, chat  # noqa


def token_auth(token):
    return snug.header_adder({'Authorization': f'Bearer {token}'})
