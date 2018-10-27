# -*- coding: utf-8 -*-
import json
import sys

import pytest

import snug

try:
    import urllib.request as urllib
except ImportError:
    import urllib2 as urllib

live = pytest.mark.skipif(not pytest.config.getoption('--live'),
                          reason='skip live data test')

py3 = pytest.mark.skipif(sys.version_info < (3, ), reason='python 3+ only')


def test_send_with_unknown_client():
    class MyClass(object):
        pass
    with pytest.raises(TypeError, match='MyClass'):
        snug.send(MyClass(), snug.GET('foo'))


def test_async_send_with_unknown_client():
    class MyClass(object):
        pass

    with pytest.raises(TypeError, match='MyClass'):
        snug.send_async(MyClass(), snug.GET('foo'))


@live
class TestSendWithUrllib:

    def test_no_contenttype(self, mocker):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['Content-Type'] == 'application/octet-stream'

    def test_no_data(self, mocker):
        req = snug.Request('GET', 'http://httpbin.org/get',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['headers']['Accept'] == 'application/json'
        assert 'Content-Type' not in data['headers']

    def test_contenttype(self, mocker):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'content-Type': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Content-Type'] == 'application/json'

    def test_non_200_success(self, mocker):
        req = snug.Request('POST', 'http://httpbin.org/status/204')
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(204, mocker.ANY, headers=mocker.ANY)

    def test_http_error_status(self, mocker):
        req = snug.Request('POST', 'http://httpbin.org/status/404')
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(404, b'', headers=mocker.ANY)
        assert response.headers['Content-Length'] == '0'


@py3
@live
class TestSendWithAsyncio:

    def test_https(self, loop, mocker):
        req = snug.Request('GET', 'https://httpbin.org/get',
                           params={'param1': 'foo'},
                           headers={'Accept': 'application/json'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['url'] == 'https://httpbin.org/get?param1=foo'
        assert data['args'] == {'param1': 'foo'}
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['User-Agent'].startswith('Python-asyncio/')

    def test_http(self, loop, mocker):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=json.dumps({"foo": 4}).encode(),
                           headers={'User-agent': 'snug/dev'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['url'] == 'http://httpbin.org/post'
        assert data['args'] == {}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['User-Agent'] == 'snug/dev'

    def test_nonascii_headers(self, loop, mocker):
        req = snug.Request('GET', 'http://httpbin.org/get',
                           headers={'X-Foo': 'blå'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['url'] == 'http://httpbin.org/get'
        assert data['args'] == {}
        assert data['headers']['X-Foo'] == 'blå'

    def test_head(self, loop, mocker):
        req = snug.Request('HEAD', 'http://httpbin.org/anything',
                           headers={'X-Foo': 'foo'})
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, b'', headers=mocker.ANY)
        assert 'Content-Type' in response.headers

    def test_timeout(self, loop):
        import asyncio

        req = snug.Request('GET', 'http://httpbin.org/delay/2')
        with pytest.raises(asyncio.TimeoutError):
            loop.run_until_complete(
                snug.send_async(loop, req, timeout=.5))

    def test_redirects(self, loop, mocker):
        req = snug.Request('GET', 'http://httpbin.org/redirect/4')
        response = loop.run_until_complete(snug.send_async(loop, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)

    def test_too_many_redirects(self, loop, mocker):
        req = snug.Request('GET', 'http://httpbin.org/redirect/3')
        response = loop.run_until_complete(
            snug.send_async(loop, req, max_redirects=1))
        assert response == snug.Response(302, mocker.ANY, headers=mocker.ANY)


@live
def test_requests_send(mocker):
    requests = pytest.importorskip("requests")
    session = requests.Session()

    req = snug.POST('https://httpbin.org/post',
                    content=b'{"foo": 4}',
                    params={'bla': '99'},
                    headers={'Accept': 'application/json'})

    response = snug.send(session, req)
    assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
    data = json.loads(response.content.decode())
    assert data['args'] == {'bla': '99'}
    assert json.loads(data['data']) == {'foo': 4}
    assert data['headers']['Accept'] == 'application/json'


@py3
@live
class TestAiohttpSend:

    def test_ok(self, loop, mocker):
        from .py3_only import using_aiohttp

        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': '99'},
                        headers={'Accept': 'application/json'})

        response = loop.run_until_complete(using_aiohttp(req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'bla': '99'}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['Accept'] == 'application/json'

    def test_error(self, loop, mocker):
        pytest.importorskip('aiohttp')
        from .py3_only import error, using_aiohttp

        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': '99'},
                        headers={'Accept': 'application/json'})
        mocker.patch('aiohttp.client_reqrep.ClientResponse.read', error)

        with pytest.raises(ValueError, match='foo'):
            loop.run_until_complete(using_aiohttp(req))
