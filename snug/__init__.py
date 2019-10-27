"""
The entire public API is available at root level::

    from snug import Query, Request, send_async, PATCH, paginated, ...
"""
from . import clients, http
from .__about__ import *  # noqa
from .clients import *  # noqa
from .http import *  # noqa
from .pagination import *  # noqa
from .query import *  # noqa

__all__ = ["clients", "http"]
