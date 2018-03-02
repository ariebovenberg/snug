import asyncio
import sys
import urllib.request
from functools import partial
from http.client import HTTPResponse
from io import BytesIO
from itertools import starmap

from .http import Response, send, send_async

_ASYNCIO_USER_AGENT = 'Python-asyncio/3.{}'.format(sys.version_info.minor)


class _SocketAdaptor:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


@send.register(urllib.request.OpenerDirector)
def _urllib_send(opener, req, **kwargs):
    """Send a request with an :mod:`urllib` opener"""
    if req.content and not any(h.lower() == 'content-type'
                               for h in req.headers):
        req = req.with_headers({'Content-Type': 'application/octet-stream'})
    url = req.url + '?' + urllib.parse.urlencode(req.params)
    raw_req = urllib.request.Request(url, req.content, headers=req.headers,
                                     method=req.method)
    res = urllib.request.urlopen(raw_req, **kwargs)
    return Response(res.getcode(), content=res.read(), headers=res.headers)


@send_async.register(asyncio.AbstractEventLoop)
@asyncio.coroutine
def _asyncio_send(loop, req):
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
        writer.write(b'\r\n'.join([headers.encode(), b'', req.content or b'']))
        response_bytes = BytesIO((yield from reader.read()))
    finally:
        writer.close()
    resp = HTTPResponse(_SocketAdaptor(response_bytes))
    resp.begin()
    return Response(resp.getcode(), content=resp.read(), headers=resp.headers)


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


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:
    @send.register(requests.Session)
    def _requests_send(session, req):
        """send a request with the `requests` library"""
        res = session.request(req.method, req.url,
                              data=req.content,
                              params=req.params,
                              headers=req.headers)
        return Response(res.status_code, res.content, headers=res.headers)
