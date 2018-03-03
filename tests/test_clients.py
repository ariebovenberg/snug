import inspect
import json
import sys

import pytest
from gentools import py2_compatible, return_

import snug

try:
    import urllib.request as urllib
    from unittest import mock
except ImportError:
    import urllib2 as urllib
    import mock

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

    def test_no_contenttype(self):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Accept'] == 'application/json'
        assert data['headers']['Content-Type'] == 'application/octet-stream'

    def test_no_data(self):
        req = snug.Request('GET', 'http://httpbin.org/get',
                           headers={'Accept': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['headers']['Accept'] == 'application/json'
        assert 'Content-Type' not in data['headers']

    def test_contenttype(self):
        req = snug.Request('POST', 'http://httpbin.org/post',
                           content=b'foo',
                           headers={'content-Type': 'application/json'},
                           params={'foo': 'bar'})
        client = urllib.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'foo': 'bar'}
        assert data['data'] == 'foo'
        assert data['headers']['Content-Type'] == 'application/json'


@py3
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


@py3
@live
class TestAiohttpSend:

    def test_ok(self, loop):
        from .py3_only import using_aiohttp

        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': 99},
                        headers={'Accept': 'application/json'})

        response = loop.run_until_complete(using_aiohttp(req))
        assert response == snug.Response(200, mock.ANY, headers=mock.ANY)
        data = json.loads(response.content.decode())
        assert data['args'] == {'bla': '99'}
        assert json.loads(data['data']) == {'foo': 4}
        assert data['headers']['Accept'] == 'application/json'

    def test_error(self, loop):
        pytest.importorskip('aiohttp')
        from .py3_only import error, using_aiohttp

        req = snug.POST('https://httpbin.org/post',
                        content=b'{"foo": 4}',
                        params={'bla': 99},
                        headers={'Accept': 'application/json'})
        with mock.patch('aiohttp.client_reqrep.ClientResponse.read', error):
            with pytest.raises(ValueError, match='foo'):
                loop.run_until_complete(using_aiohttp(req))


@py3
def test__execute_async__(loop):
    from .py3_only import awaitable

    class StringClient:
        def __init__(self, mappings):
            self.mappings = mappings

        def send(self, req):
            return self.mappings[req]

    snug.send_async.register(StringClient, StringClient.send)

    client = StringClient({
        'foo/posts/latest': awaitable('redirect:/posts/latest/'),
        'foo/posts/latest/': awaitable('redirect:/posts/december/'),
        'foo/posts/december/': awaitable(b'hello world'),
    })

    class MyQuery:

        @py2_compatible
        def __iter__(self):
            redirect = yield '/posts/latest'
            redirect = yield redirect.split(':')[1]
            response = yield redirect.split(':')[1]
            return_(response.decode('ascii'))

    future = snug.Query.__execute_async__(
        MyQuery(),
        client=client,
        authenticate=lambda s: 'foo' + s)

    if sys.version_info > (3, 5):
        assert inspect.isawaitable(future)

    result = loop.run_until_complete(future)
    assert result == 'hello world'


@py3
class TestExecuteAsync:

    def test_defaults(self, loop):
        import asyncio
        from .py3_only import awaitable

        with mock.patch('snug._async.send_async',
                        return_value=awaitable(snug.Response(204))) as send:

            @py2_compatible
            def myquery():
                return_((yield snug.GET('my/url')))

            future = snug.execute_async(myquery())
            result = loop.run_until_complete(future)
            assert result == snug.Response(204)
            client, req = send.call_args[0]
            assert isinstance(client, asyncio.AbstractEventLoop)
            assert req == snug.GET('my/url')

    def test_custom_client(self, loop):
        from .py3_only import MockAsyncClient
        client = MockAsyncClient(snug.Response(204))

        @py2_compatible
        def myquery():
            return_((yield snug.GET('my/url')))

        future = snug.execute_async(myquery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_custom_execute(self, loop):
        from .py3_only import MockAsyncClient
        client = MockAsyncClient(snug.Response(204))

        class MyQuery:
            def __execute_async__(self, client, authenticate):
                return client.send(snug.GET('my/url'))

        future = snug.execute_async(MyQuery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_auth(self, loop):
        from .py3_only import MockAsyncClient
        client = MockAsyncClient(snug.Response(204))

        @py2_compatible
        def myquery():
            return_((yield snug.GET('my/url')))

        future = snug.execute_async(myquery(),
                                    auth=('user', 'pw'),
                                    client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})

    def test_auth_method(self, loop):
        from .py3_only import MockAsyncClient

        def token_auth(token, request):
            return request.with_headers({
                'Authorization': 'Bearer {}'.format(token)
            })

        @py2_compatible
        def myquery():
            return_((yield snug.GET('my/url')))

        client = MockAsyncClient(snug.Response(204))
        future = snug.execute_async(myquery(), auth='foo', client=client,
                                    auth_method=token_auth)
        result = loop.run_until_complete(future)

        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Bearer foo'})
