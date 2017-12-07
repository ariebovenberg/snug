"""a toolkit for wrapping REST APIs"""
from .http import *  # noqa
from .query import Query, Api, resolve, simple_resolve  # noqa
from .wrap import Wrapper  # noqa

from . import http, load, query, xml  # noqa

from .__about__ import __version__, __author__, __copyright__  # noqa
