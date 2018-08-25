"""Patch in async-exclusive functionality. Only for python 3+"""
import asyncio
import sys
import typing as t
import urllib.request
from functools import partial
from http.client import HTTPResponse
from io import BytesIO
from itertools import starmap

from .clients import send_async
from .compat import HAS_PEP492
from .http import Response
from .query import Query

T = t.TypeVar('T')
_ASYNCIO_USER_AGENT = 'Python-asyncio/3.{}'.format(sys.version_info.minor)


class _SocketAdaptor:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


@send_async.register(asyncio.AbstractEventLoop)
@asyncio.coroutine
def _asyncio_send(loop, req, *, timeout=10, max_redirects=10):
    """A rudimentary HTTP client using :mod:`asyncio`"""
    if not any(h.lower() == 'user-agent' for h in req.headers):
        req = req.with_headers({'User-Agent': _ASYNCIO_USER_AGENT})
    url = urllib.parse.urlsplit(
        req.url + '?' + urllib.parse.urlencode(req.params))
    open_ = partial(asyncio.open_connection, url.hostname, loop=loop)
    connect = open_(443, ssl=True) if url.scheme == 'https' else open_(80)
    reader, writer = yield from connect
    try:
        headers = '\r\n'.join([
            '{} {} HTTP/1.1'.format(req.method, url.path + '?' + url.query),
            'Host: ' + url.hostname,
            'Connection: close',
            'Content-Length: {}'.format(len(req.content or b'')),
            '\r\n'.join(starmap('{}: {}'.format, req.headers.items())),
        ])
        writer.write(b'\r\n'.join([headers.encode('latin-1'),
                                   b'', req.content or b'']))
        response_bytes = BytesIO(
            (yield from asyncio.wait_for(reader.read(), timeout=timeout)))
    finally:
        writer.close()
    resp = HTTPResponse(_SocketAdaptor(response_bytes),
                        method=req.method, url=req.url)
    resp.begin()
    status = resp.getcode()
    if 300 <= status < 400 and 'Location' in resp.headers and max_redirects:
        new_url = urllib.parse.urljoin(req.url, resp.headers['Location'])
        return (yield from _asyncio_send(
            loop, req.replace(url=new_url),
            timeout=timeout,
            max_redirects=max_redirects-1))
    return Response(status, content=resp.read(), headers=resp.headers)


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:
    @send_async.register(aiohttp.ClientSession)
    @asyncio.coroutine
    def _aiohttp_send(session, req):
        """send a request with the `aiohttp` library"""
        # this is basically a simplified `async with`
        # in py3.4 compatible syntax
        # see https://www.python.org/dev/peps/pep-0492/#new-syntax
        resp = yield from session.request(
            req.method, req.url,
            params=req.params,
            data=req.content,
            headers=req.headers).__aenter__()
        try:
            content = yield from resp.read()
        finally:
            yield from resp.__aexit__(None, None, None)
        return Response(resp.status, content=content, headers=resp.headers)


@partial(setattr, Query, '__execute_async__')
@asyncio.coroutine
def __execute_async__(self, client, auth):
    """Default asynchronous execution logic for a query,
    which uses the query's :meth:`~Query.__iter__`.
    May be overriden for full control of query execution,
    at the cost of reusability.

    .. versionadded:: 1.1

    Note
    ----
    You shouldn't need to override this method, except in rare cases
    where implementing :meth:`Query.__iter__` does not suffice.

    Parameters
    ----------
    client
        the client instance passed to :func:`execute_async`
    auth: ~typing.Callable[[Request], Request]
        a callable to authenticate a :class:`~snug.http.Request`

    Returns
    -------
    T
        the query result
    """
    gen = iter(self)
    request = next(gen)
    while True:
        response = yield from send_async(client, auth(request))
        try:
            request = gen.send(response)
        except StopIteration as e:
            return e.value


class AsyncPaginator(t.AsyncIterator[T] if HAS_PEP492 else object):
    """An async iterator which keeps executing
    the next query in the page sequence"""
    __slots__ = '_executor', '_next_query'

    def __init__(self, next_query, executor):
        self._next_query, self._executor = next_query, executor

    def __aiter__(self):
        return self

    @asyncio.coroutine
    def __anext__(self):
        """the content of the next page"""
        if self._next_query is None:
            raise StopAsyncIteration()
        page = yield from self._executor(self._next_query)
        self._next_query = page.next_query
        return page.content
