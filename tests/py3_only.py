"""python 3 only objects.
In a separate module to prevent syntax-errors on python 2"""
import asyncio

import pytest

import snug


async def error(self):
    await asyncio.sleep(0)
    raise ValueError('foo')


async def using_aiohttp(req):
    aiohttp = pytest.importorskip('aiohttp')
    session = aiohttp.ClientSession()
    try:
        return await snug.send_async(session, req)
    finally:
        await session.close()


async def awaitable(obj):
    """an awaitable returning given object"""
    await asyncio.sleep(0)
    return obj


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    async def send(self, req):
        await asyncio.sleep(0)
        self.request = req
        return self.response


async def consume_aiter(iterable):
    """consume an async iterable to a list"""
    result = []
    async for item in iterable:
        result.append(item)
    return result


snug.send_async.register(MockAsyncClient, MockAsyncClient.send)
