"""an ORM toolkit for wrapping REST APIs"""
from .http import Request, Response  # noqa
from .query import Query, Api, resolve  # noqa

from . import http, load, query  # noqa

from .__about__ import __version__, __author__, __copyright__  # noqa
