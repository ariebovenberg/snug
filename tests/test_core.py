from functools import partial
from operator import methodcaller
from unittest import mock

import pytest

import snug


class MockClient:
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


@snug.make_sender.register(MockClient)
def _sender(client):
    return client.send


def test_execute():
    sender = {
        '/posts/latest': 'redirect:/posts/latest/',
        '/posts/latest/': 'redirect:/posts/december/',
        '/posts/december/': b'hello world'
    }.__getitem__

    class MyQuery:
        def __iter__(self):
            redirect = yield '/posts/latest'
            redirect = yield redirect.split(':')[1]
            response = yield redirect.split(':')[1]
            return response.decode('ascii')

    assert snug.execute(MyQuery(), sender) == 'hello world'


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

    def test_with_basic_auth(self):
        req = snug.GET('my/url/', headers={'foo': 'bar'})
        newreq = req.with_basic_auth(('Aladdin', 'OpenSesame'))
        assert newreq == snug.GET(
            'my/url/', headers={
                'foo': 'bar',
                'Authorization': 'Basic QWxhZGRpbjpPcGVuU2VzYW1l'
            })

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


class TestExecutor:

    @mock.patch('urllib.request.Request', autospec=True)
    @mock.patch('urllib.request.urlopen', autospec=True)
    def test_defaults_to_urllib(self, urlopen, urllib_request):
        exec = snug.executor()

        def myquery():
            return (yield snug.GET('my/url'))

        assert exec(myquery()) == snug.Response(
            status_code=urlopen.return_value.getcode.return_value,
            data=urlopen.return_value.read.return_value,
            headers=urlopen.return_value.headers,
        )

    def test_custom_client(self):
        client = MockClient(snug.Response(204))
        exec = snug.executor(client=client)

        def myquery():
            return (yield snug.GET('my/url'))

        assert exec(myquery()) == snug.Response(204)
        assert client.request == snug.GET('my/url')

    def test_authentication(self):
        client = MockClient(snug.Response(204))
        exec = snug.executor(('user', 'pw'), client=client)

        def myquery():
            return (yield snug.GET('my/url'))

        assert exec(myquery()) == snug.Response(204)
        assert client.request == snug.GET(
            'my/url', headers={'Authorization': 'Basic dXNlcjpwdw=='})


def test_sender_factory_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        snug.make_sender(MyClass())


@mock.patch('urllib.request.Request', autospec=True)
@mock.patch('urllib.request.urlopen', autospec=True)
def test_urllib_sender(urlopen, urllib_request):
    req = snug.Request('HEAD', 'https://www.api.github.com/organizations',
                       params={'since': 3043},
                       headers={'Accept': 'application/vnd.github.v3+json'})
    response = snug.urllib_sender(req, timeout=10)
    assert response == snug.Response(
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
    sender = snug.make_sender(session)
    req = snug.GET('https://www.api.github.com/organizations',
                   params={'since': 3043},
                   headers={'Accept': 'application/vnd.github.v3+json'})
    response = sender(req)
    assert response == snug.Response(
        status_code=session.request.return_value.status_code,
        data=session.request.return_value.content,
        headers=session.request.return_value.headers,
    )
    session.request.assert_called_once_with(
        'GET',
        'https://www.api.github.com/organizations',
        params={'since': 3043},
        headers={'Accept': 'application/vnd.github.v3+json'})


def test_related():

    class Foo:

        @snug.related
        class Bar:
            def __init__(self, a, b):
                self.a, self.b = a, b

    f = Foo()
    bar = f.Bar(4)
    assert isinstance(bar, Foo.Bar)

    bar2 = Foo.Bar(f, 4)
    assert isinstance(bar2, Foo.Bar)
