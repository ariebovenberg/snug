"""wrapper for the github API"""
from functools import partial
from dataclasses import dataclass

import snug

from .types import *  # noqa
from . import channels, chat  # noqa


@dataclass
class TokenAuth:
    """token-based authentication"""
    token: str

    def __call__(self, request):
        return request.with_headers({
            'Authorization': f'Bearer {self.token}'
        })


executor = partial(snug.executor, auth_factory=TokenAuth)
async_executor = partial(snug.async_executor, auth_factory=TokenAuth)

execute = executor()
execute_async = async_executor()
