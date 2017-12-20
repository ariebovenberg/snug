import asyncio

import pytest

import snug


@pytest.mark.asyncio
async def test_resolve_async(async_resolver, query, Post):
    response = await snug.asyn.resolve(async_resolver, query)
    assert response == [
        Post(5, 'hello world'),
        Post(6, 'goodbye'),
    ]


@pytest.mark.asyncio
async def test_piped_sender(jsonwrapper):

    async def _sender(request):
        await asyncio.sleep(0)
        return snug.Response(
            404,
            data='{{"error": "{} not found"}}'.format(request.url)
            .encode('ascii'))

    sender = snug.asyn.PipedSender(_sender, pipe=jsonwrapper)
    response = await sender(snug.Request('my/url', {'foo': 4}))
    assert response == {'error': 'my/url not found'}
