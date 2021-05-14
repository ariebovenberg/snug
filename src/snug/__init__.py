"""
The entire public API is available at root level::

    from snug import Query, Request, send_async, PATCH, paginated, ...
"""
from . import clients, http
from .clients import *  # noqa
from .http import *  # noqa
from .pagination import *  # noqa
from .query import *  # noqa

# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)


__all__ = ["clients", "http"]
