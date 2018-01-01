import asyncio

import pytest

import snug


@pytest.mark.asyncio
async def test_execute_async():

    async def sender(req):
        await asyncio.sleep(0)
        if not req.endswith('/'):
            return 'redirect:' + req + '/'
        elif req == '/posts/latest/':
            return 'hello world'

    class MyQuery:
        def __resolve__(self):
            response = yield '/posts/latest'
            while response.startswith('redirect:'):
                response = yield response[9:]
            return response.upper()

    query = MyQuery()
    assert await snug.asnc.exec(sender, query) == 'HELLO WORLD'
    assert await snug.asnc.exec(sender, query.__resolve__()) == 'HELLO WORLD'


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
