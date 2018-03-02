import asyncio
import json
import urllib.request
from unittest import mock

import pytest

import snug


live = pytest.mark.skipif(not pytest.config.getoption('--live'),
                          reason='skip live data test')


@asyncio.coroutine
def error(self):
    yield from asyncio.sleep(0)
    raise ValueError('foo')


class TestSendWithUrllib:

    @live
    def test_no_contenttype(self):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['Content-Type'] == 'application/octet-stream'

    @live
    def test_no_data(self):
        req = snug.Request('GET', 'http://httpbin.org/get',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['headers']['Accept'] == 'application/json'
        assert 'Content-Type' not in data['headers']

    @live
    def test_contenttype(self):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'content-Type': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Content-Type'] == 'application/json'


def test_requests_send():
    requests = pytest.importorskip("requests")
    session = mock.Mock(spec=requests.Session)
    req = snug.GET('https://www.api.github.com/organizations',
                   params={'since': 3043},
                   headers={'Accept': 'application/vnd.github.v3+json'})
    req = snug.POST('http://httpbin.org/post',
                    content=b'foo',
                    params={'bla': 5},
                    headers={'User-Agent': 'snug/dev'})
    response = snug.send(session, req)
    assert response == snug.Response(
        status_code=session.request.return_value.status_code,
        content=session.request.return_value.content,
        headers=session.request.return_value.headers,
    )
    session.request.assert_called_once_with(
        'POST',
        'http://httpbin.org/post',
        data=b'foo',
        params={'bla': 5},
        headers={'User-Agent': 'snug/dev'})


@live
class TestSendWithAsyncio:

    def test_https(self, loop):
        req = snug.Request('GET', 'https://httpbin.org/get',
                           params={'param1': 'foo'},
                           headers={'Accept': 'application/json'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['url'] == 'https://httpbin.org/get?param1=foo'
        assert data['args'] == {'param1': 'foo'}
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['User-Agent'].startswith('Python-asyncio/')

    def test_http(self, loop):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=json.dumps({"foo": 4}).encode(),
                           headers={'User-agent': 'snug/dev'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['url'] == 'http://httpbin.org/post'
        assert data['args'] == {}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['User-Agent'] == 'snug/dev'


@live
class TestAiohttpSend:

    def test_ok(self, loop):
        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': 99},
                        headers={'Accept': 'application/json'})
        aiohttp = pytest.importorskip('aiohttp')

        @asyncio.coroutine
        def do_test():
            session = aiohttp.ClientSession()
            try:
                return (yield from snug.send_async(session, req))
            finally:
                yield from session.close()

        response = loop.run_until_complete(do_test())
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'bla': '99'}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['Accept'] == 'application/json'

    def test_error(self, loop):
        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': 99},
                        headers={'Accept': 'application/json'})
        aiohttp = pytest.importorskip('aiohttp')

        @asyncio.coroutine
        def do_test():
            session = aiohttp.ClientSession()
            try:
                return (yield from snug.send_async(session, req))
            finally:
                yield from session.close()

        with mock.patch('aiohttp.client_reqrep.ClientResponse.read', error):
            with pytest.raises(ValueError, match='foo'):
                loop.run_until_complete(do_test())
