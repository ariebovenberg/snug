import asyncio

import pytest

import snug


@pytest.mark.asyncio
async def test_execute_async():

    async def sender(req):
        assert req == '/posts/latest/'
        await asyncio.sleep(0)
        return b'hello world'

    class MyQuery:
        def __resolve__(self):
            return (yield '/posts/latest/').decode('ascii')

    assert await snug.asnc.execute(sender, MyQuery()) == 'hello world'


@pytest.mark.asyncio
async def test_piped_sender():

    def ascii_encode(req):
        return (yield req.encode('ascii')).decode('ascii')

    async def sender(req):
        assert req == b'/posts/latest/'
        await asyncio.sleep(0)
        return b'hello world'

    sender = snug.asnc.PipedSender(ascii_encode, sender)
    response = await sender('/posts/latest/')
    assert response == 'hello world'
