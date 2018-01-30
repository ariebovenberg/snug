import asyncio
import json
from functools import partial
from operator import methodcaller
from unittest import mock

import pytest

import snug

live = pytest.config.getoption('--live')


@pytest.fixture
def loop():
    return asyncio.get_event_loop()


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    @asyncio.coroutine
    def send(self, req):
        yield from asyncio.sleep(0)
        self.request = req
        return self.response


@snug.make_async_sender.register(MockAsyncClient)
def _async_sender(client):
    return client.send


def test_async_sender_factory_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        snug.make_async_sender(MyClass())


def test_execute_async(loop):

    @asyncio.coroutine
    def sender(req):
        yield from asyncio.sleep(0)
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
    result = loop.run_until_complete(snug.execute_async(query, sender=sender))
    assert result == 'HELLO WORLD'


@pytest.mark.skipif(not live, reason='skip live data test')
class TestAsyncioSender:

    def test_https(self, loop):
        req = snug.Request('GET', 'https://httpbin.org/get',
                           params={'param1': 'foo'},
                           headers={'Accept': 'application/json'})
        response = loop.run_until_complete(snug.asyncio_sender(req))
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'param1': 'foo'}
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['User-Agent'].startswith('Python-asyncio/')

    def test_http(self, loop):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=json.dumps({"foo": 4}).encode(),
                           headers={'User-Agent': 'snug/dev'})
        response = loop.run_until_complete(snug.asyncio_sender(req))
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['User-Agent'] == 'snug/dev'


class TestAsyncExecutor:

    def test_defaults_to_asyncio_sender(self):
        exec = snug.async_executor()
        assert exec.keywords['sender'].funcs[0] is snug.asyncio_sender

    def test_custom_client(self, loop):
        client = MockAsyncClient(snug.Response(204))
        exec = snug.async_executor(client=client)

        def myquery():
            return (yield snug.GET('my/url'))

        assert loop.run_until_complete(exec(myquery())) == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_authentication(self, loop):
        client = MockAsyncClient(snug.Response(204))
        exec = snug.async_executor(('user', 'pw'),
                                   client=client,
                                   auth_factory=partial(methodcaller,
                                                        'with_basic_auth'))

        def myquery():
            return (yield snug.GET('my/url'))

        assert loop.run_until_complete(exec(myquery())) == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})


def test_aiohttp_sender(loop):
    req = snug.GET('https://test.com',
                   content=b'{"foo": 4}',
                   params={'bla': 99},
                   headers={'Authorization': 'Basic ABC'})
    aiohttp = pytest.importorskip('aiohttp')
    from aioresponses import aioresponses

    @asyncio.coroutine
    def do_test():
        session = aiohttp.ClientSession()
        try:
            sender = snug.make_async_sender(session)
            return (yield from sender(req))
        finally:
            session.close()

    with aioresponses() as m:
        m.get('https://test.com/?bla=99', body=b'{"my": "content"}',
              status=201,
              headers={'Content-Type': 'application/json'})
        response = loop.run_until_complete(do_test())

        assert response == snug.Response(
            201,
            content=b'{"my": "content"}',
            headers={'Content-Type': 'application/json'})

        call, = m.requests[('GET', 'https://test.com/?bla=99')]
        assert call.kwargs['headers'] == {'Authorization': 'Basic ABC'}
        assert call.kwargs['params'] == {'bla': 99}
        assert call.kwargs['data'] == b'{"foo": 4}'
