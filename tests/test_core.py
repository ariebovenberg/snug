import asyncio
import inspect
import sys
import urllib.request
from unittest import mock

import pytest

import snug

live = pytest.mark.skipif(not pytest.config.getoption('--live'),
                          reason='skip live data test')


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


def test_executor():
    exec = snug.executor(client='foo')
    assert exec.keywords == {'client': 'foo'}


def test_async_executor():
    exec = snug.async_executor(client='foo')
    assert exec.keywords == {'client': 'foo'}


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


def test_identity():
    obj = object()
    assert snug.core._identity(obj) is obj
