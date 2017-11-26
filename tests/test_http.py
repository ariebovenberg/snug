from unittest import mock

import pytest

from snug import http


class TestRequest:

    def test_defaults(self):
        req = http.Request('my/url/')
        assert req == http.Request(
            'my/url/',
            params={},
            headers={},
            method='GET'
        )

    def test_add_headers(self):
        req = http.Request('my/url', headers={'foo': 'bla'})
        assert req.add_headers({'other-header': 3}) == http.Request(
            'my/url', headers={'foo': 'bla', 'other-header': 3})

    def test_add_prefix(self):
        req = http.Request('my/url/')
        assert req.add_prefix('mysite.com/') == http.Request(
            'mysite.com/my/url/')

    def test_add_params(self):
        req = http.Request('my/url/', params={'foo': 'bar'})
        assert req.add_params({'other': 3}) == http.Request(
            'my/url/', params={'foo': 'bar', 'other': 3})

    def test_add_basic_auth(self):
        req = http.Request('my/url/', headers={'foo': 'bar'})
        newreq = req.add_basic_auth(('Aladdin', 'OpenSesame'))
        assert newreq == http.Request(
            'my/url/', headers={
                'foo': 'bar',
                'Authorization': 'Basic QWxhZGRpbjpPcGVuU2VzYW1l'
            })


@mock.patch('urllib.request.Request', autospec=True)
@mock.patch('urllib.request.urlopen', autospec=True)
def test_urllib_sender(urlopen, urllib_request):
    sender = http.urllib_sender(timeout=10)
    req = http.Request('https://www.api.github.com/organizations',
                       params={'since': 3043},
                       headers={'Accept': 'application/vnd.github.v3+json'})
    response = sender(req)
    assert response == http.Response(
        status_code=urlopen.return_value.getcode.return_value,
        content=urlopen.return_value.read.return_value,
        headers=urlopen.return_value.headers,
        )
    urlopen.assert_called_once_with(urllib_request.return_value, timeout=10)
    urllib_request.assert_called_once_with(
        'https://www.api.github.com/organizations?since=3043',
        headers={'Accept': 'application/vnd.github.v3+json'}
    )


def test_requests_sender():
    pytest.importorskip("requests")
    session = mock.Mock()
    sender = http.requests_sender(session)
    req = http.Request('https://www.api.github.com/organizations',
                       params={'since': 3043},
                       headers={'Accept': 'application/vnd.github.v3+json'})
    response = sender(req)
    assert response == http.Response(
        status_code=session.get.return_value.status_code,
        content=session.get.return_value.content,
        headers=session.get.return_value.headers,
    )
    session.get.assert_called_once_with(
        'https://www.api.github.com/organizations',
        params={'since': 3043},
        headers={'Accept': 'application/vnd.github.v3+json'})
