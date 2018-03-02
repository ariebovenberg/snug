import asyncio
import inspect
import json
import sys
import urllib.request
from unittest import mock

import pytest

import snug

live = pytest.mark.skipif(not pytest.config.getoption('--live'),
                          reason='skip live data test')


@pytest.fixture
def loop(scope='module'):
    return asyncio.get_event_loop()


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    @asyncio.coroutine
    def send(self, req):
        yield from asyncio.sleep(0)
        self.request = req
        return self.response


class MockClient:
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)
snug.send_async.register(MockAsyncClient, MockAsyncClient.send)


@asyncio.coroutine
def awaitable(obj):
    """an awaitable returning given object"""
    yield from asyncio.sleep(0)
    return obj


def test__execute__():

    class StringClient:
        def __init__(self, mappings):
            self.mappings = mappings

        def send(self, req):
            return self.mappings[req]

    snug.send.register(StringClient, StringClient.send)

    client = StringClient({
        'foo/posts/latest': 'redirect:/posts/latest/',
        'foo/posts/latest/': 'redirect:/posts/december/',
        'foo/posts/december/': b'hello world'
    })

    class MyQuery:
        def __iter__(self):
            redirect = yield '/posts/latest'
            redirect = yield redirect.split(':')[1]
            response = yield redirect.split(':')[1]
            return response.decode('ascii')

    assert snug.Query.__execute__(
        MyQuery(),
        client=client,
        authenticate=lambda s: 'foo' + s) == 'hello world'


def test__execute_async__(loop):

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
        def __iter__(self):
            redirect = yield '/posts/latest'
            redirect = yield redirect.split(':')[1]
            response = yield redirect.split(':')[1]
            return response.decode('ascii')

    future = snug.Query.__execute_async__(
        MyQuery(),
        client=client,
        authenticate=lambda s: 'foo' + s)

    if sys.version_info > (3, 5):
        assert inspect.isawaitable(future)

    result = loop.run_until_complete(future)
    assert result == 'hello world'


class TestExecute:

    @mock.patch('snug.core.send', autospec=True)
    def test_defaults(self, send):

        def myquery():
            return (yield snug.GET('my/url'))

        assert snug.execute(myquery()) == send.return_value
        client, req = send.call_args[0]
        assert isinstance(client, urllib.request.OpenerDirector)
        assert req == snug.GET('my/url')

    def test_custom_client(self):
        client = MockClient(snug.Response(204))

        def myquery():
            return (yield snug.GET('my/url'))

        result = snug.execute(myquery(), client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_custom_execute(self):
        client = MockClient(snug.Response(204))

        class MyQuery:
            def __execute__(self, client, authenticate):
                return client.send(snug.GET('my/url'))

        result = snug.execute(MyQuery(), client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_auth(self):
        client = MockClient(snug.Response(204))

        def myquery():
            return (yield snug.GET('my/url'))

        result = snug.execute(myquery(),
                              auth=('user', 'pw'),
                              client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})

    def test_auth_method(self):

        def token_auth(token, request):
            return request.with_headers({
                'Authorization': 'Bearer {}'.format(token)
            })

        def myquery():
            return (yield snug.GET('my/url'))

        client = MockClient(snug.Response(204))
        result = snug.execute(myquery(), auth='foo', client=client,
                              auth_method=token_auth)

        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Bearer foo'})


class TestExecuteAsync:

    @mock.patch('snug.core.send_async',
                return_value=awaitable(snug.Response(204)))
    def test_defaults(self, send, loop):

        def myquery():
            return (yield snug.GET('my/url'))

        future = snug.execute_async(myquery())
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        client, req = send.call_args[0]
        assert isinstance(client, asyncio.AbstractEventLoop)
        assert req == snug.GET('my/url')

    def test_custom_client(self, loop):
        client = MockAsyncClient(snug.Response(204))

        def myquery():
            return (yield snug.GET('my/url'))

        future = snug.execute_async(myquery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_custom_execute(self, loop):
        client = MockAsyncClient(snug.Response(204))

        class MyQuery:
            def __execute_async__(self, client, authenticate):
                return client.send(snug.GET('my/url'))

        future = snug.execute_async(MyQuery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_auth(self, loop):
        client = MockAsyncClient(snug.Response(204))

        def myquery():
            return (yield snug.GET('my/url'))

        future = snug.execute_async(myquery(),
                                    auth=('user', 'pw'),
                                    client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})

    def test_auth_method(self, loop):

        def token_auth(token, request):
            return request.with_headers({
                'Authorization': 'Bearer {}'.format(token)
            })

        def myquery():
            return (yield snug.GET('my/url'))

        client = MockAsyncClient(snug.Response(204))
        future = snug.execute_async(myquery(), auth='foo', client=client,
                                    auth_method=token_auth)
        result = loop.run_until_complete(future)

        assert result == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Bearer foo'})


class TestRequest:

    def test_defaults(self):
        req = snug.Request('GET', 'my/url/')
        assert req == snug.Request('GET', 'my/url/', params={}, headers={})

    def test_with_headers(self):
        req = snug.GET('my/url', headers={'foo': 'bla'})
        assert req.with_headers({'other-header': 3}) == snug.GET(
            'my/url', headers={'foo': 'bla', 'other-header': 3})

    def test_with_prefix(self):
        req = snug.GET('my/url/')
        assert req.with_prefix('mysite.com/') == snug.GET(
            'mysite.com/my/url/')

    def test_with_params(self):
        req = snug.GET('my/url/', params={'foo': 'bar'})
        assert req.with_params({'other': 3}) == snug.GET(
            'my/url/', params={'foo': 'bar', 'other': 3})

    def test_equality(self):
        req = snug.Request('GET', 'my/url')
        other = req.replace()
        assert req == other
        assert not req != other

        assert not req == req.replace(headers={'foo': 'bar'})
        assert req != req.replace(headers={'foo': 'bar'})

        assert not req == object()
        assert req != object()

    def test_repr(self):
        req = snug.GET('my/url')
        assert 'GET my/url' in repr(req)


class TestResponse:

    def test_equality(self):
        rsp = snug.Response(204)
        other = rsp.replace()
        assert rsp == other
        assert not rsp != other

        assert not rsp == rsp.replace(headers={'foo': 'bar'})
        assert rsp != rsp.replace(headers={'foo': 'bar'})

        assert not rsp == object()
        assert rsp != object()

    def test_repr(self):
        assert '404' in repr(snug.Response(404))


def test_prefix_adder():
    req = snug.GET('my/url')
    adder = snug.prefix_adder('mysite.com/')
    assert adder(req) == snug.GET('mysite.com/my/url')


def test_header_adder():
    req = snug.GET('my/url', headers={'Accept': 'application/json'})
    adder = snug.header_adder({
        'Authorization': 'my-auth'
    })
    assert adder(req) == snug.GET('my/url', headers={
        'Accept': 'application/json',
        'Authorization': 'my-auth'
    })


def test_executor():
    exec = snug.executor(client='foo')
    assert exec.keywords == {'client': 'foo'}


def test_async_executor():
    exec = snug.async_executor(client='foo')
    assert exec.keywords == {'client': 'foo'}


def test_send_with_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        snug.send(MyClass(), snug.GET('foo'))


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


def test_async_send_with_unknown_client(loop):
    class MyClass:
        pass

    with pytest.raises(TypeError, match='MyClass'):
        loop.run_until_complete(snug.send_async(MyClass(), snug.GET('foo')))


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


@asyncio.coroutine
def error(self):
    yield from asyncio.sleep(0)
    raise ValueError('foo')


class TestAiohttpSend:

    @live
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

    @live
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


def test_relation():

    class Foo:

        @snug.related
        class Bar(snug.Query):
            def __iter__(self): pass

            def __init__(self, a, b):
                self.a, self.b = a, b

        class Qux(snug.Query):
            def __iter__(self): pass

            def __init__(self, a, b):
                self.a, self.b = a, b

    f = Foo()
    bar = f.Bar(b=4)
    assert isinstance(bar, Foo.Bar)
    assert bar.a is f
    bar2 = Foo.Bar(f, 4)
    assert isinstance(bar2, Foo.Bar)
    assert bar.a is f

    # staticmethod opts out
    qux = f.Qux(1, 2)
    assert isinstance(qux, f.Qux)
    qux2 = Foo.Qux(1, 2)
    assert isinstance(qux2, Foo.Qux)


@pytest.fixture
def headers():
    return snug.Headers({
        'Content-Type': 'application/json',
        'accept': 'text/plain'
    })


class AlwaysEquals:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class AlwaysInEquals:
    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True


class TestHeaders:

    def test_empty(self):
        headers = snug.Headers()
        assert len(headers) == 0
        with pytest.raises(KeyError, match='foo'):
            assert headers['foo']
        assert list(headers) == []
        assert headers == {}

    def test_getitem(self, headers):
        assert headers['Content-Type'] == 'application/json'
        assert headers['content-type'] == 'application/json'
        assert headers['Accept'] == 'text/plain'
        assert headers['ACCEPT'] == 'text/plain'

    def test_iter(self, headers):
        assert set(headers) == {'Content-Type', 'accept'}

    def test_equality(self, headers):
        assert headers == headers
        equivalent = {
            'Accept': 'text/plain',
            'Content-TYPE': 'application/json',
        }
        assert headers == equivalent
        assert headers == snug.Headers(equivalent)
        assert hash(headers) == hash(snug.Headers(equivalent))

        assert not headers == {
            'Content-Type': 'application/json',
        }
        assert not headers == snug.Headers({
            'Content-Type': 'application/json',
        })

        assert not headers == {
            'Content-TYPE': 'application/pdf',
            'Accept': 'text/plain'
        }
        assert headers == AlwaysEquals()
        assert not headers == AlwaysInEquals()

    def test_inequality(self, headers):
        assert not headers != headers
        equivalent = {
            'Accept': 'text/plain',
            'Content-TYPE': 'application/json',
        }
        assert not headers != equivalent
        assert not headers != snug.Headers(equivalent)
        assert headers != {
            'Content-Type': 'application/json',
        }
        assert headers != {
            'Content-TYPE': 'application/pdf',
            'Accept': 'text/plain'
        }
        assert hash(headers) != hash(snug.Headers({
            'Content-TYPE': 'application/pdf',
            'Accept': 'text/plain'
        }))
        assert not headers != AlwaysEquals()
        assert headers != AlwaysInEquals()

    def test_items(self, headers):
        assert set(headers.items()) == {
            ('Content-Type', 'application/json'),
            ('accept', 'text/plain'),
        }

    def test_keys(self, headers):
        assert 'Content-Type' in headers.keys()
        assert 'Content-type' in headers.keys()
        assert 'Content-Disposition' not in headers.keys()
        assert set(headers.keys()) == {'Content-Type', 'accept'}

    def test_len(self, headers):
        assert len(headers) == 2

    def test_bool(self, headers):
        assert headers
        assert not snug.Headers()

    def test_contains(self, headers):
        assert 'Content-Type' in headers
        assert 'Content-type' in headers
        assert 'ACCEPT' in headers
        assert 'Content-Disposition' not in headers

    def test_asdict(self, headers):
        assert dict(headers) == {
            'Content-Type': 'application/json',
            'accept': 'text/plain'
        }

    def test_values(self, headers):
        assert set(headers.values()) == {'application/json', 'text/plain'}

    def test_get(self, headers):
        assert headers.get('Content-Type', 'foo') == 'application/json'
        assert headers.get('Content-TYPE', None) == 'application/json'
        assert headers.get('Accept', None) == 'text/plain'
        assert headers.get('Cookie', 'foo') == 'foo'

    def test_repr(self, headers):
        rep = repr(headers)
        for key, value in headers.items():
            assert key in rep
            assert value in rep

        assert repr(snug.Headers()) == '{<empty>}'


def test_identity():
    obj = object()
    assert snug.core._identity(obj) is obj
