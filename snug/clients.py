"""Funtions for dealing with for HTTP clients in a unified manner"""
from .compat import (set_urllib_method, singledispatch, urlencode,
                     urllib_request)
from .http import Response

__all__ = ['send', 'send_async']


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
    raise TypeError('client {!r} not registered'.format(client))


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

        Note
        ----
        ``aiohttp`` is only supported on python 3.5.3+

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
    raise TypeError('client {!r} not registered'.format(client))


@send.register(urllib_request.OpenerDirector)
def _urllib_send(opener, req, **kwargs):
    """Send a request with an :mod:`urllib` opener"""
    if req.content and not any(h.lower() == 'content-type'
                               for h in req.headers):
        req = req.with_headers({'Content-Type': 'application/octet-stream'})
    url = req.url + '?' + urlencode(req.params)
    raw_req = urllib_request.Request(url, req.content, headers=req.headers)
    set_urllib_method(raw_req, req.method)
    res = opener.open(raw_req, **kwargs)
    return Response(res.getcode(), content=res.read(), headers=res.headers)


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
