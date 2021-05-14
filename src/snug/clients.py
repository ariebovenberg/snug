"""Funtions for dealing with for HTTP clients in a unified manner"""
import asyncio
import sys
import urllib.request
from functools import partial, singledispatch
from http.client import HTTPResponse
from io import BytesIO
from itertools import starmap
from urllib.error import HTTPError
from urllib.parse import urlencode

from .http import Response

__all__ = ["send", "send_async"]


_ASYNCIO_USER_AGENT = "Python-asyncio/3.{}".format(sys.version_info.minor)


@singledispatch
def send(client, request):
    """Given a client, send a :class:`~snug.http.Request`,
    returning a :class:`~snug.http.Response`.

    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        The client with which to send the request.

        Client types registered by default:

        * :class:`urllib.request.OpenerDirector`
          (e.g. from :func:`~urllib.request.build_opener`)
        * :class:`requests.Session`
          (if `requests <http://docs.python-requests.org/>`_ is installed)

    request: Request
        The request to send

    Returns
    -------
    Response
        the resulting response


    Example of registering a new HTTP client:

    >>> @send.register(MyClientClass)
    ... def _send(client, request: Request) -> Response:
    ...     r = client.send(request)
    ...     return Response(r.status, r.read(), headers=r.get_headers())
    """
    raise TypeError("client {!r} not registered".format(client))


@singledispatch
def send_async(client, request):
    """Given a client, send a :class:`~snug.http.Request`,
    returning an awaitable :class:`~snug.http.Response`.

    A :func:`~functools.singledispatch` function.

    Parameters
    ----------
    client: any registered client type
        The client with which to send the request.

        Client types supported by default:

        * :class:`asyncio.AbstractEventLoop`
          (e.g. from :func:`~asyncio.get_event_loop`)
        * :class:`aiohttp.ClientSession`
          (if `aiohttp <http://aiohttp.readthedocs.io/>`_ is installed)

    request: Request
        The request to send

    Returns
    -------
    Response
        the resulting response


    Example of registering a new HTTP client:

    >>> @send_async.register(MyClientClass)
    ... async def _send(client, request: Request) -> Response:
    ...     r = await client.send(request)
    ...     return Response(r.status, r.read(), headers=r.get_headers())
    """
    raise TypeError("client {!r} not registered".format(client))


@send.register(urllib.request.OpenerDirector)
def _urllib_send(opener, req, **kwargs):
    """Send a request with an :mod:`urllib` opener"""
    if req.content and not any(
        h.lower() == "content-type" for h in req.headers
    ):
        req = req.with_headers({"Content-Type": "application/octet-stream"})
    url = req.url + "?" + urlencode(req.params)
    raw_req = urllib.request.Request(url, req.content, headers=req.headers)
    raw_req.method = req.method
    try:
        res = opener.open(raw_req, **kwargs)
    except HTTPError as http_err:
        res = http_err
    return Response(res.getcode(), content=res.read(), headers=res.headers)


class _SocketAdaptor:
    def __init__(self, io):
        self._file = io

    def makefile(self, *args, **kwargs):
        return self._file


@send_async.register(asyncio.AbstractEventLoop)
async def _asyncio_send(loop, req, *, timeout=10, max_redirects=10):
    """A rudimentary HTTP client using :mod:`asyncio`"""
    if not any(h.lower() == "user-agent" for h in req.headers):
        req = req.with_headers({"User-Agent": _ASYNCIO_USER_AGENT})
    url = urllib.parse.urlsplit(
        req.url + "?" + urllib.parse.urlencode(req.params)
    )
    open_ = partial(asyncio.open_connection, url.hostname, loop=loop)
    connect = open_(443, ssl=True) if url.scheme == "https" else open_(80)
    reader, writer = await connect
    try:
        headers = "\r\n".join(
            [
                "{} {} HTTP/1.1".format(
                    req.method, url.path + "?" + url.query
                ),
                "Host: " + url.hostname,
                "Connection: close",
                "Content-Length: {}".format(len(req.content or b"")),
                "\r\n".join(starmap("{}: {}".format, req.headers.items())),
            ]
        )
        writer.write(
            b"\r\n".join([headers.encode("latin-1"), b"", req.content or b""])
        )
        response_bytes = BytesIO(
            await asyncio.wait_for(reader.read(), timeout=timeout)
        )
    finally:
        writer.close()
    resp = HTTPResponse(
        _SocketAdaptor(response_bytes), method=req.method, url=req.url
    )
    resp.begin()
    status = resp.getcode()
    if 300 <= status < 400 and "Location" in resp.headers and max_redirects:
        new_url = urllib.parse.urljoin(req.url, resp.headers["Location"])
        return await _asyncio_send(
            loop,
            req.replace(url=new_url),
            timeout=timeout,
            max_redirects=max_redirects - 1,
        )
    return Response(status, content=resp.read(), headers=resp.headers)


try:
    import requests
except ImportError:  # pragma: no cover
    pass
else:

    @send.register(requests.Session)
    def _requests_send(session, req):
        """send a request with the `requests` library"""
        res = session.request(
            req.method,
            req.url,
            data=req.content,
            params=req.params,
            headers=req.headers,
        )
        return Response(res.status_code, res.content, headers=res.headers)


try:
    import aiohttp
except ImportError:  # pragma: no cover
    pass
else:

    @send_async.register(aiohttp.ClientSession)
    async def _aiohttp_send(session, req):
        """send a request with the `aiohttp` library"""
        async with session.request(
            req.method,
            req.url,
            params=req.params,
            data=req.content,
            headers=req.headers,
        ) as resp:
            return Response(
                resp.status, content=await resp.read(), headers=resp.headers
            )
