from unittest import mock

import pytest
import requests

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


class TestResponse:

    def test_parse_content(self):
        resp = http.Response(200, 'my content', {})
        assert resp.parse_content('[{}]'.format)


class TestSend:

    def test_invalid_client(self):

        class MyClass():
            pass

        with pytest.raises(TypeError, match='MyClass'):
            http.send(MyClass(), http.Request('my/url/'))

    def test_with_requests_session(self):
        req = http.Request('my/url/',
                           headers={'my-header': 'foo'},
                           params={'param1': 4})
        client = requests.Session()

        with mock.patch.object(client, 'get', autospec=True) as getter:
            response = http.send(client, req)

        getter.assert_called_once_with('my/url/',
                                       headers={'my-header': 'foo'},
                                       params={'param1': 4})
        raw_response = getter.return_value
        assert raw_response.raise_for_status.called
        assert response == http.Response(
            raw_response.status_code,
            content=raw_response.content,
            headers=raw_response.headers,
        )
