"""
The entire public API is available at root level::

    from snug import Query, Request, send_async, PATCH, paginated, ...
"""
import sys

from . import clients, http
from .__about__ import *  # noqa
from .clients import *  # noqa
from .http import *  # noqa
from .pagination import *  # noqa
from .query import *  # noqa

if sys.version_info > (3,):  # pragma: no cover
    from . import _async  # noqa


__all__ = ["clients", "http"]
