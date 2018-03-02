import pytest

import snug


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


def test_send_with_unknown_client():
    class MyClass:
        pass
    with pytest.raises(TypeError, match='MyClass'):
        snug.send(MyClass(), snug.GET('foo'))


def test_async_send_with_unknown_client(loop):
    class MyClass:
        pass

    with pytest.raises(TypeError, match='MyClass'):
        loop.run_until_complete(snug.send_async(MyClass(), snug.GET('foo')))


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
