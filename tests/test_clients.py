import asyncio
import json
import urllib.request

import pytest

import snug


async def error(self):
    await asyncio.sleep(0)
    raise ValueError("foo")


async def awaitable(obj):
    """an awaitable returning given object"""
    await asyncio.sleep(0)
    return obj


async def using_aiohttp(req):
    aiohttp = pytest.importorskip("aiohttp")
    session = aiohttp.ClientSession()
    try:
        return await snug.send_async(session, req)
    finally:
        await session.close()


async def using_httpx_async(req):
    httpx = pytest.importorskip("httpx")
    async with httpx.AsyncClient() as client:
        return await snug.send_async(client, req)


def using_httpx_sync(req):
    httpx = pytest.importorskip("httpx")
    with httpx.Client() as client:
        return snug.send(client, req)


def test_send_with_unknown_client():
    class MyClass(object):
        pass

    with pytest.raises(TypeError, match="MyClass"):
        snug.send(MyClass(), snug.GET("foo"))


def test_async_send_with_unknown_client():
    class MyClass(object):
        pass

    with pytest.raises(TypeError, match="MyClass"):
        snug.send_async(MyClass(), snug.GET("foo"))


class TestSendWithUrllib:
    def test_no_contenttype(self, mocker, httpbin):
        req = snug.Request(
            "POST",
            httpbin.url + "/post",
            content=b"foo",
            headers={"Accept": "application/json"},
            params={"foo": "bar"},
        )
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["args"] == {"foo": "bar"}
        assert data["data"] == "foo"
        assert data["headers"]["Accept"] == "application/json"
        assert data["headers"]["Content-Type"] == "application/octet-stream"

    def test_no_data(self, mocker, httpbin):
        req = snug.Request(
            "GET",
            httpbin.url + "/get",
            headers={"Accept": "application/json"},
            params={"foo": "bar"},
        )
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["args"] == {"foo": "bar"}
        assert data["headers"]["Accept"] == "application/json"
        assert "Content-Type" not in data["headers"]

    def test_contenttype(self, mocker, httpbin):
        req = snug.Request(
            "POST",
            httpbin.url + "/post",
            content=b"foo",
            headers={"content-Type": "application/json"},
            params={"foo": "bar"},
        )
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["args"] == {"foo": "bar"}
        assert data["data"] == "foo"
        assert data["headers"]["Content-Type"] == "application/json"

    def test_non_200_success(self, mocker, httpbin):
        req = snug.Request("POST", httpbin.url + "/status/204")
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(204, mocker.ANY, headers=mocker.ANY)

    def test_http_error_status(self, mocker, httpbin):
        req = snug.Request("POST", httpbin.url + "/status/404")
        client = urllib.request.build_opener()
        response = snug.send(client, req)
        assert response == snug.Response(404, b"", headers=mocker.ANY)
        assert response.headers["Content-Length"] == "0"


@pytest.mark.live
class TestSendWithAsyncio:
    def test_https(self, mocker):
        req = snug.Request(
            "GET",
            "http://httpbingo.org/get",
            params={"param1": "foo"},
            headers={"Accept": "application/json"},
        )
        response = asyncio.run(snug.send_async(None, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["url"].split(":", 1)[1] == "//httpbingo.org/get?param1=foo"
        assert data["args"] == {"param1": ["foo"]}
        assert data["headers"]["Accept"] == ["application/json"]
        assert data["headers"]["User-Agent"][0].startswith("Python-asyncio/")

    def test_http(self, mocker):
        req = snug.Request(
            "POST",
            "http://httpbingo.org/post",
            content=json.dumps({"foo": 4}).encode(),
            headers={
                "User-agent": "snug/dev",
                "Content-Type": "application/json",
            },
        )
        response = asyncio.run(snug.send_async(None, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["url"].split(":", 1)[1] == "//httpbingo.org/post?"
        assert data["args"] == {}
        assert json.loads(data["data"]) == {"foo": 4}
        assert data["headers"]["User-Agent"] == ["snug/dev"]

    @pytest.mark.skip(reason="unresolved, rare issue")
    def test_nonascii_headers(self, mocker):
        req = snug.Request(
            "GET", "http://httpbingo.org/get", headers={"X-Foo": "blå"}
        )
        response = asyncio.run(snug.send_async(None, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["url"].split(":", 1)[1] == "//httpbingo.org/get?"
        assert data["args"] == {}
        breakpoint()
        assert data["headers"]["X-Foo"] == ["blå"]

    def test_head(self, mocker, httpbin):
        req = snug.Request(
            "HEAD", "http://httpbingo.org/anything", headers={"X-Foo": "foo"}
        )
        response = asyncio.run(snug.send_async(None, req))
        assert response == snug.Response(200, b"", headers=mocker.ANY)
        assert "Content-Type" in response.headers

    def test_timeout(self):
        req = snug.Request("GET", "http://httpbingo.org/delay/2")
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(snug.send_async(None, req, timeout=0.5))

    def test_redirects(self, mocker):
        req = snug.Request("GET", "http://httpbingo.org/redirect/4")
        response = asyncio.run(snug.send_async(None, req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)

    def test_too_many_redirects(self, mocker):
        req = snug.Request("GET", "http://httpbingo.org/redirect/3")
        response = asyncio.run(snug.send_async(None, req, max_redirects=1))
        assert response == snug.Response(302, mocker.ANY, headers=mocker.ANY)


def test_requests_send(mocker, httpbin):
    requests = pytest.importorskip("requests")
    session = requests.Session()

    req = snug.POST(
        httpbin.url + "/post",
        content=b'{"foo": 4}',
        params={"bla": "99"},
        headers={"Accept": "application/json"},
    )

    response = snug.send(session, req)
    assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
    data = json.loads(response.content.decode())
    assert data["args"] == {"bla": "99"}
    assert json.loads(data["data"]) == {"foo": 4}
    assert data["headers"]["Accept"] == "application/json"


class TestAiohttpSend:
    def test_ok(self, mocker, httpbin):
        req = snug.POST(
            httpbin.url + "/post",
            content=b'{"foo": 4}',
            params={"bla": "99"},
            headers={"Accept": "application/json"},
        )

        response = asyncio.run(using_aiohttp(req))
        assert response == snug.Response(200, mocker.ANY, headers=mocker.ANY)
        data = json.loads(response.content.decode())
        assert data["args"] == {"bla": "99"}
        assert json.loads(data["data"]) == {"foo": 4}
        assert data["headers"]["Accept"] == "application/json"

    def test_error(self, mocker, httpbin):
        pytest.importorskip("aiohttp")

        req = snug.POST(
            httpbin.url + "/post",
            content=b'{"foo": 4}',
            params={"bla": "99"},
            headers={"Accept": "application/json"},
        )
        mocker.patch("aiohttp.client_reqrep.ClientResponse.read", error)

        with pytest.raises(ValueError, match="foo"):
            asyncio.run(using_aiohttp(req))


class TestHttpxSend:
    def test_ok_sync(self, mocker, httpbin):
        req = snug.POST(
            httpbin.url + "/post",
            content=b'{"foo": 4}',
            params={"bla": "99"},
            headers={"Accept": "application/json"},
        )
        response = using_httpx_sync(req)
        assert snug.Response(200, mocker.ANY, mocker.ANY) == response
        data = json.loads(response.content.decode())
        assert data["args"] == {"bla": "99"}
        assert json.loads(data["data"]) == {"foo": 4}
        assert data["headers"]["Accept"] == "application/json"

    def test_ok_async(self, mocker, httpbin):
        req = snug.POST(
            httpbin.url + "/post",
            content=b'{"foo": 4}',
            params={"bla": "99"},
            headers={"Accept": "application/json"},
        )
        response = asyncio.run(using_httpx_async(req))
        assert snug.Response(200, mocker.ANY, mocker.ANY) == response
        data = json.loads(response.content.decode())
        assert data["args"] == {"bla": "99"}
        assert json.loads(data["data"]) == {"foo": 4}
        assert data["headers"]["Accept"] == "application/json"
