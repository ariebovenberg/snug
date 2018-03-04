from collections import Counter, OrderedDict

import pytest

import snug
from snug.compat import PY3


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

        assert req == AlwaysEquals()
        assert not req != AlwaysEquals()
        assert req != AlwaysInEquals()
        assert not req == AlwaysInEquals()

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
