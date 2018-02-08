"""wrapper for the github API"""
from functools import partial

import snug

from .types import *  # noqa
from . import channels, chat  # noqa


def token_auth(token, request):
    return request.with_headers({
        'Authorization': f'Bearer {token}'
    })


executor = partial(snug.executor, auth_method=token_auth)
async_executor = partial(snug.async_executor, auth_method=token_auth)
execute = partial(executor, auth_method=token_auth)
execute_async = partial(async_executor, auth_method=token_auth)
