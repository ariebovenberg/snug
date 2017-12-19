"""a toolkit for wrapping REST APIs"""
from .abc import *  # noqa
from .http import *  # noqa
from .query import (Query, resolve, resolve_async,  # noqa
                    build_resolver, build_async_resolver)
from .pipe import Pipe  # noqa

from . import http, load, query, xml  # noqa

from .__about__ import __version__, __author__, __copyright__  # noqa
