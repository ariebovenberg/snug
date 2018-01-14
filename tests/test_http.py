from functools import partial
from unittest import mock
from operator import methodcaller

import pytest

from snug import http


class MockClient:
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


@http.sender.register(MockClient)
def _sender(client):
    return client.send


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    async def send(self, req):
        self.request = req
        return self.response


@http.async_sender.register(MockAsyncClient)
def _async_sender(client):
    return client.send


class TestRequest:

    def test_defaults(self):
        req = http.Request('GET', 'my/url/')
        assert req == http.Request('GET', 'my/url/', params={}, headers={})

    def test_with_headers(self):
        req = http.GET('my/url', headers={'foo': 'bla'})
        assert req.with_headers({'other-header': 3}) == http.GET(
            'my/url', headers={'foo': 'bla', 'other-header': 3})

    def test_with_prefix(self):
        req = http.GET('my/url/')
        assert req.with_prefix('mysite.com/') == http.GET(
            'mysite.com/my/url/')

    def test_with_params(self):
        req = http.GET('my/url/', params={'foo': 'bar'})
        assert req.with_params({'other': 3}) == http.GET(
            'my/url/', params={'foo': 'bar', 'other': 3})

    def test_with_basic_auth(self):
        req = http.GET('my/url/', headers={'foo': 'bar'})
        newreq = req.with_basic_auth(('Aladdin', 'OpenSesame'))
        assert newreq == http.GET(
            'my/url/', headers={
                'foo': 'bar',
                'Authorization': 'Basic QWxhZGRpbjpPcGVuU2VzYW1l'
            })

    def test_equality(self):
        req = http.Request('GET', 'my/url')
        other = req.replace()
        assert req == other
        assert not req != other

        assert not req == req.replace(headers={'foo': 'bar'})
        assert req != req.replace(headers={'foo': 'bar'})

        assert not req == object()
        assert req != object()

    def test_repr(self):
        req = http.GET('my/url')
        assert 'GET my/url' in repr(req)


class TestResponse:

    def test_equality(self):
        rsp = http.Response(204)
        other = rsp.replace()
        assert rsp == other
        assert not rsp != other

        assert not rsp == rsp.replace(headers={'foo': 'bar'})
        assert rsp != rsp.replace(headers={'foo': 'bar'})

        assert not rsp == object()
        assert rsp != object()

    def test_repr(self):
        assert '404' in repr(http.Response(404))


def test_prefix_adder():
    req = http.GET('my/url')
    adder = http.prefix_adder('mysite.com/')
    assert adder(req) == http.GET('mysite.com/my/url')


def test_header_adder():
    req = http.GET('my/url', headers={'Accept': 'application/json'})
    adder = http.header_adder({
        'Authorization': 'my-auth'
    })
    assert adder(req) == http.GET('my/url', headers={
        'Accept': 'application/json',
        'Authorization': 'my-auth'
    })


class TestExecutor:

    @mock.patch('urllib.request.Request', autospec=True)
    @mock.patch('urllib.request.urlopen', autospec=True)
    def test_defaults_to_urllib(self, urlopen, urllib_request):
        exec = http.executor()

        def myquery():
            return (yield http.GET('my/url'))

        assert exec(myquery()) == http.Response(
            status_code=urlopen.return_value.getcode.return_value,
            data=urlopen.return_value.read.return_value,
            headers=urlopen.return_value.headers,
        )

    def test_custom_client(self):
        client = MockClient(http.Response(204))
        exec = http.executor(client=client)

        def myquery():
            return (yield http.GET('my/url'))

        assert exec(myquery()) == http.Response(204)
        assert client.request == http.GET('my/url')

    def test_authentication(self):
        client = MockClient(http.Response(204))
        exec = http.executor(('user', 'pw'),
                             client=client,
                             authenticator=partial(methodcaller,
                                                   'with_basic_auth'))

        def myquery():
            return (yield http.GET('my/url'))

        assert exec(myquery()) == http.Response(204)
        assert client.request == http.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})


def test_optional_basic_auth():
    no_auth = http.optional_basic_auth(None)
    assert no_auth(http.GET('foo')) == http.GET('foo')

    authed = http.optional_basic_auth(('user', 'pw'))
    assert authed(http.GET('foo')) == http.GET('foo', headers={
        'Authorization': 'Basic dXNlcjpwdw=='
    })


def test_sender_factory_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        http.sender(MyClass())


def test_async_sender_factory_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        http.async_sender(MyClass())


class TestAsyncExecutor:

    @pytest.mark.asyncio
    async def test_custom_client(self):
        client = MockAsyncClient(http.Response(204))
        exec = http.async_executor(client=client)

        def myquery():
            return (yield http.GET('my/url'))

        assert await exec(myquery()) == http.Response(204)
        assert client.request == http.GET('my/url')

    @pytest.mark.asyncio
    async def test_authentication(self):
        client = MockAsyncClient(http.Response(204))
        exec = http.async_executor(('user', 'pw'),
                                   client=client,
                                   authenticator=partial(methodcaller,
                                                         'with_basic_auth'))

        def myquery():
            return (yield http.GET('my/url'))

        assert await exec(myquery()) == http.Response(204)
        assert client.request == http.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})


@mock.patch('urllib.request.Request', autospec=True)
@mock.patch('urllib.request.urlopen', autospec=True)
def test_urllib_sender(urlopen, urllib_request):
    req = http.Request('HEAD', 'https://www.api.github.com/organizations',
                       params={'since': 3043},
                       headers={'Accept': 'application/vnd.github.v3+json'})
    response = http.urllib_sender(req, timeout=10)
    assert response == http.Response(
        status_code=urlopen.return_value.getcode.return_value,
        data=urlopen.return_value.read.return_value,
        headers=urlopen.return_value.headers,
    )
    urlopen.assert_called_once_with(urllib_request.return_value, timeout=10)
    urllib_request.assert_called_once_with(
        'https://www.api.github.com/organizations?since=3043',
        headers={'Accept': 'application/vnd.github.v3+json'},
        method='HEAD',
    )


def test_requests_sender():
    requests = pytest.importorskip("requests")
    session = mock.Mock(spec=requests.Session)
    sender = http.sender(session)
    req = http.GET('https://www.api.github.com/organizations',
                   params={'since': 3043},
                   headers={'Accept': 'application/vnd.github.v3+json'})
    response = sender(req)
    assert response == http.Response(
        status_code=session.request.return_value.status_code,
        data=session.request.return_value.content,
        headers=session.request.return_value.headers,
    )
    session.request.assert_called_once_with(
        'GET',
        'https://www.api.github.com/organizations',
        params={'since': 3043},
        headers={'Accept': 'application/vnd.github.v3+json'})


@pytest.mark.asyncio
async def test_aiohttp_sender():
    req = http.GET('https://test.com',
                   data=b'{"foo": 4}',
                   params={'bla': 99},
                   headers={'Authorization': 'Basic ABC'})
    aiohttp = pytest.importorskip('aiohttp')
    from aioresponses import aioresponses

    with aioresponses() as m:
        m.get('https://test.com/?bla=99', body=b'{"my": "content"}',
              status=201,
              headers={'Content-Type': 'application/json'})

        async with aiohttp.ClientSession() as session:
            sender = http.async_sender(session)
            response = await sender(req)

        assert response == http.Response(
            201,
            data=b'{"my": "content"}',
            headers={'Content-Type': 'application/json'})

        call, = m.requests[('GET', 'https://test.com/?bla=99')]
        assert call.kwargs['headers'] == {'Authorization': 'Basic ABC'}
        assert call.kwargs['params'] == {'bla': 99}
        assert call.kwargs['data'] == b'{"foo": 4}'
