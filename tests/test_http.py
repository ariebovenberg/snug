from unittest import mock
from dataclasses import dataclass

import pytest

from snug import http


@dataclass
class SingleSender:
    response: http.Response
    request:  http.Request = None

    def __call__(self, request):
        self.request = request
        return self.response


@dataclass
class SingleAsyncSender:
    response: http.Response
    request:  http.Request = None

    async def __call__(self, request):
        self.request = request
        return self.response


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


def test_simple_exec():
    exec = http.simple_exec(sender={'foo': 'bar'}.__getitem__)

    def myquery():
        return (yield 'foo').upper()
    assert exec(myquery()) == 'BAR'


def test_authed_exec():
    sender = SingleSender(http.Response(204))
    exec = http.authed_exec(auth=('foo', 'bar'), sender=sender)

    def myquery():
        return (yield http.GET('foo')).status_code

    assert exec(myquery()) == 204
    assert sender.request.url == 'foo'
    assert sender.request.headers['Authorization'].startswith('Basic')


@pytest.mark.asyncio
async def test_authed_aexec():
    sender = SingleAsyncSender(http.Response(204))
    exec = http.authed_aexec(auth=('foo', 'bar'), sender=sender)

    def myquery():
        return (yield http.GET('foo')).status_code

    assert await exec(myquery()) == 204
    assert sender.request.url == 'foo'
    assert sender.request.headers['Authorization'].startswith('Basic')


@mock.patch('urllib.request.Request', autospec=True)
@mock.patch('urllib.request.urlopen', autospec=True)
def test_urllib_sender(urlopen, urllib_request):
    sender = http.urllib_sender(timeout=10)
    req = http.Request('HEAD', 'https://www.api.github.com/organizations',
                       params={'since': 3043},
                       headers={'Accept': 'application/vnd.github.v3+json'})
    response = sender(req)
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
    sender = http.requests_sender(session)
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
            sender = http.aiohttp_sender(session)
            response = await sender(req)

        assert response == http.Response(
            201,
            data=b'{"my": "content"}',
            headers={'Content-Type': 'application/json'})

        call, = m.requests[('GET', 'https://test.com/?bla=99')]
        assert call.kwargs['headers'] == {'Authorization': 'Basic ABC'}
        assert call.kwargs['params'] == {'bla': 99}
        assert call.kwargs['data'] == b'{"foo": 4}'
