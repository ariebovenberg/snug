"""python 3 only objects.
In a separate module to prevent syntax-errors on python 2"""
import asyncio

import pytest

import snug


@asyncio.coroutine
def error(self):
    yield from asyncio.sleep(0)
    raise ValueError('foo')


@asyncio.coroutine
def using_aiohttp(req):
    aiohttp = pytest.importorskip('aiohttp')
    session = aiohttp.ClientSession()
    try:
        return (yield from snug.send_async(session, req))
    finally:
        yield from session.close()


@asyncio.coroutine
def awaitable(obj):
    """an awaitable returning given object"""
    yield from asyncio.sleep(0)
    return obj


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    @asyncio.coroutine
    def send(self, req):
        yield from asyncio.sleep(0)
        self.request = req
        return self.response


snug.send_async.register(MockAsyncClient, MockAsyncClient.send)
