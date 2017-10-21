"""an ORM toolkit for wrapping REST APIs"""
from .http import Request  # noqa
from .query import Query, Api  # noqa

from . import http, load, query  # noqa

from .__about__ import __version__, __author__, __copyright__  # noqa
