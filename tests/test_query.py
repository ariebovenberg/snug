import asyncio
import inspect
import urllib.request
from operator import methodcaller

import snug


async def awaitable(obj):
    """an awaitable returning given object"""
    await asyncio.sleep(0)
    return obj


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    async def send(self, req):
        await asyncio.sleep(0)
        self.request = req
        return self.response


snug.send_async.register(MockAsyncClient, MockAsyncClient.send)


class MockClient(object):
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)


def test__execute__():
    class StringClient:
        def __init__(self, mappings):
            self.mappings = mappings

        def send(self, req):
            return self.mappings[req]

    snug.send.register(StringClient, StringClient.send)

    client = StringClient(
        {
            "foo/posts/latest": "redirect:/posts/latest/",
            "foo/posts/latest/": "redirect:/posts/december/",
            "foo/posts/december/": b"hello world",
        }
    )

    class MyQuery(object):
        def __iter__(self):
            redirect = yield "/posts/latest"
            redirect = yield redirect.split(":")[1]
            response = yield redirect.split(":")[1]
            return response.decode("ascii")

    assert (
        snug.Query.__execute__(MyQuery(), client, lambda s: "foo" + s)
        == "hello world"
    )


def myquery():
    return (yield snug.GET("my/url"))


class TestExecute:
    def test_defaults(self, mocker):
        send = mocker.patch("snug.query.send", autospec=True)

        assert snug.execute(myquery()) == send.return_value
        client, req = send.call_args[0]
        assert isinstance(client, urllib.request.OpenerDirector)
        assert req == snug.GET("my/url")

    def test_custom_client(self):
        client = MockClient(snug.Response(204))

        result = snug.execute(myquery(), client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_custom_execute(self):
        client = MockClient(snug.Response(204))

        class MyQuery(object):
            def __execute__(self, client, auth):
                return client.send(snug.GET("my/url"))

        result = snug.execute(MyQuery(), client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_auth(self):
        client = MockClient(snug.Response(204))

        result = snug.execute(myquery(), auth=("user", "pw"), client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            "my/url", headers={"Authorization": "Basic dXNlcjpwdw=="}
        )

    def test_none_auth(self):
        client = MockClient(snug.Response(204))

        result = snug.execute(myquery(), auth=None, client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_auth_callable(self):
        client = MockClient(snug.Response(204))
        auther = methodcaller("with_headers", {"X-My-Auth": "letmein"})

        result = snug.execute(myquery(), auth=auther, client=client)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            "my/url", headers={"X-My-Auth": "letmein"}
        )


class TestExecuteAsync:
    def test_defaults(self, loop, mocker):
        send = mocker.patch(
            "snug.query.send_async", return_value=awaitable(snug.Response(204))
        )

        future = snug.execute_async(myquery())
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        client, req = send.call_args[0]
        assert isinstance(client, asyncio.AbstractEventLoop)
        assert req == snug.GET("my/url")

    def test_custom_client(self, loop):

        client = MockAsyncClient(snug.Response(204))

        future = snug.execute_async(myquery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_custom_execute(self, loop):

        client = MockAsyncClient(snug.Response(204))

        class MyQuery:
            def __execute_async__(self, client, auth):
                return client.send(snug.GET("my/url"))

        future = snug.execute_async(MyQuery(), client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_auth(self, loop):

        client = MockAsyncClient(snug.Response(204))

        future = snug.execute_async(
            myquery(), auth=("user", "pw"), client=client
        )
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            "my/url", headers={"Authorization": "Basic dXNlcjpwdw=="}
        )

    def test_none_auth(self, loop):

        client = MockAsyncClient(snug.Response(204))

        future = snug.execute_async(myquery(), auth=None, client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET("my/url")

    def test_auth_callable(self, loop):

        client = MockAsyncClient(snug.Response(204))
        auther = methodcaller("with_headers", {"X-My-Auth": "letmein"})

        future = snug.execute_async(myquery(), auth=auther, client=client)
        result = loop.run_until_complete(future)
        assert result == snug.Response(204)
        assert client.request == snug.GET(
            "my/url", headers={"X-My-Auth": "letmein"}
        )


def test_executor():
    executor = snug.executor(client="foo")
    assert executor.keywords == {"client": "foo"}


def test_async_executor():
    executor = snug.async_executor(client="foo")
    assert executor.keywords == {"client": "foo"}


def test_relation():
    class Foo:
        @snug.related
        class Bar(snug.Query):
            def __iter__(self):
                pass

            def __init__(self, a, b):
                self.a, self.b = a, b

        class Qux(snug.Query):
            def __iter__(self):
                pass

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
    assert snug.query._identity(obj) is obj


def test__execute_async__(loop):
    class StringClient:
        def __init__(self, mappings):
            self.mappings = mappings

        def send(self, req):
            return self.mappings[req]

    snug.send_async.register(StringClient, StringClient.send)

    client = StringClient(
        {
            "foo/posts/latest": awaitable("redirect:/posts/latest/"),
            "foo/posts/latest/": awaitable("redirect:/posts/december/"),
            "foo/posts/december/": awaitable(b"hello world"),
        }
    )

    class MyQuery:
        def __iter__(self):
            redirect = yield "/posts/latest"
            redirect = yield redirect.split(":")[1]
            response = yield redirect.split(":")[1]
            return response.decode("ascii")

    future = snug.Query.__execute_async__(
        MyQuery(), client, lambda s: "foo" + s
    )

    assert inspect.isawaitable(future)

    result = loop.run_until_complete(future)
    assert result == "hello world"
