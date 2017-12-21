import asyncio
from unittest import mock

import pytest

import snug
from snug.utils import genresult


class TestJsonData:

    def test_simple(self):
        pipe = snug.lib.jsonpipe(
            snug.Request('my/url', {'foo': 6}))
        assert next(pipe) == snug.Request('my/url', b'{"foo": 6}')
        response = genresult(pipe, snug.Response(404, b'{"error": 9}'))
        assert response == {'error': 9}

    def test_no_data(self):
        pipe = snug.lib.jsonpipe(snug.Request('my/url'))
        assert next(pipe) == snug.Request('my/url')
        assert genresult(pipe, snug.Response(404)) is None


def test_build_resolver(jsonwrapper, Post):

    def sender(request):
        assert 'Authorization' in request.headers
        assert request.url == 'posts/99/'
        return snug.Response(200, b'{"id": 99, "title": "hello"}')

    @snug.query.from_gen()
    def post(id: int):
        """get a post by id"""
        return Post(**(yield snug.Request(f'posts/{id}/')))

    resolver = snug.lib.build_resolver(
        ('username', 'hunter2'),
        send=sender,
        pipe=jsonwrapper,
        authenticator=snug.Request.add_basic_auth,
    )
    response = resolver(post(99))
    assert response == Post(id=99, title='hello')


@pytest.mark.asyncio
async def test_build_async_resolver(jsonwrapper, Post):

    async def sender(request):
        assert 'Authorization' in request.headers
        assert request.url == 'posts/99/'
        await asyncio.sleep(0)
        return snug.Response(200, b'{"id": 99, "title": "hello"}')

    @snug.query.from_gen()
    def post(id: int):
        """get a post by id"""
        return Post(**(yield snug.Request(f'posts/{id}/')))

    resolver = snug.lib.build_async_resolver(
        ('username', 'hunter2'),
        send=sender,
        pipe=jsonwrapper,
        authenticator=snug.Request.add_basic_auth,
    )
    response = await resolver(post(99))
    assert response == Post(id=99, title='hello')


@mock.patch('urllib.request.urlopen', autospec=True,
            return_value=mock.Mock(**{
                'getcode.return_value': 200,
                'headers': {},
                'read.return_value': b'{"id": 4, "title": "another post"}'
            }))
def test_simple_resolver(urlopen, Post):

    resolve = snug.lib.simple_resolver(auth=('foo', 'bar'))

    @snug.query.from_gen()
    def post(id: int):
        """a post by its ID"""
        return Post(**(yield snug.Request(f'https://localhost/posts/{id}/')))

    post_4 = post(id=4)
    response = resolve(post_4)
    assert response == Post(id=4, title='another post')
