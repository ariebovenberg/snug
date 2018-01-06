import asyncio

import pytest

import snug


@pytest.mark.asyncio
async def test_exec():

    async def sender(req):
        await asyncio.sleep(0)
        if not req.endswith('/'):
            return 'redirect:' + req + '/'
        elif req == '/posts/latest/':
            return 'hello world'

    def myquery():
        response = yield '/posts/latest'
        while response.startswith('redirect:'):
            response = yield response[9:]
        return response.upper()

    query = myquery()
    assert await snug.asnc.exec(sender, query) == 'HELLO WORLD'
