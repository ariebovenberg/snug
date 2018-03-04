"""
The entire public API is available at root level::

    from snug import Query, Request, send_async, ...
"""
import sys

from .query import *  # noqa
from .http import *  # noqa
from .clients import *  # noqa

from . import http, clients  # noqa

from .__about__ import (__author__, __copyright__,  # noqa
                        __version__, __description__)

if sys.version_info > (3, ):  # pragma: no cover
    from . import _async  # noqa
