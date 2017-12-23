import asyncio
from unittest import mock

import pytest

import snug
from snug.utils import genresult


class TestJsonData:

    def test_simple(self):
        pipe = snug.lib.jsonpipe(
            snug.http.GET('my/url', {'foo': 6}))
        assert next(pipe) == snug.http.GET('my/url', b'{"foo": 6}')
        response = genresult(pipe, snug.http.Response(404, b'{"error": 9}'))
        assert response == {'error': 9}

    def test_no_data(self):
        pipe = snug.lib.jsonpipe(snug.http.GET('my/url'))
        assert next(pipe) == snug.http.GET('my/url')
        assert genresult(pipe, snug.http.Response(404)) is None


def test_build_resolver():

    def ascii_pipe(req):
        return (yield req.encode('ascii')).decode('ascii')

    def sender(req):
        assert req[:11] == b'simon says '
        return {b'/posts/latest/': b'hello'}[req[11:]]

    class MyQuery:
        def __resolve__(self):
            return 'response: ' + (yield '/posts/latest/')

    resolver = snug.lib.build_resolver(
        'simon',
        send=sender,
        pipe=ascii_pipe,
        authenticator=lambda r, n: n.encode('ascii') + b' says ' + r
    )
    assert resolver(MyQuery()) == 'response: hello'


@pytest.mark.asyncio
async def test_build_async_resolver():

    def ascii_pipe(req):
        return (yield req.encode('ascii')).decode('ascii')

    async def send(req):
        assert req[:11] == b'simon says '
        await asyncio.sleep(0)
        return {b'/posts/latest/': b'hello'}[req[11:]]

    class MyQuery:
        def __resolve__(self):
            return 'response: ' + (yield '/posts/latest/')

    resolver = snug.lib.build_async_resolver(
        'simon',
        send=send,
        pipe=ascii_pipe,
        authenticator=lambda r, n: n.encode('ascii') + b' says ' + r
    )
    assert await resolver(MyQuery()) == 'response: hello'


@mock.patch('urllib.request.urlopen', autospec=True,
            return_value=mock.Mock(**{
                'getcode.return_value': 200,
                'headers': {},
                'read.return_value': b'hello'
            }))
def test_simple_resolver(urlopen):
    resolve = snug.lib.simple_resolver(auth=('foo', 'bar'))

    @snug.query.from_gen()
    def post(id: int) -> str:
        """a post by its ID"""
        response = yield snug.http.GET(f'http://foo.com/posts/{id}/')
        return response.data.decode()

    post_4 = post(id=4)
    assert resolve(post_4) == 'hello'
