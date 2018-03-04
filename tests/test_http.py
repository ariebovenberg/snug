from collections import Counter, OrderedDict

import pytest

import snug
from snug.compat import PY3


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

    def test_with_params_unordered(self):
        req = snug.GET('my/url/', params={'foo': 'bar'})
        assert req.with_params({'other': 3}) == snug.GET(
            'my/url/', params={'foo': 'bar', 'other': 3})

    def test_with_params_ordered(self):
        req = snug.GET('my/url/', params=[('foo', 'bar'), ('bla', 'qux')])
        assert req.with_params([('other', '3')]) == snug.GET(
            'my/url/', params=[
                ('foo', 'bar'),
                ('bla', 'qux'),
                ('other', '3')])

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
        assert not headers != AlwaysEquals()
        assert headers != AlwaysInEquals()

    def test_items(self, headers):
        assert set(headers.items()) == {
            ('Content-Type', 'application/json'),
            ('accept', 'text/plain'),
        }

    def test_keys(self, headers):
        assert 'Content-Type' in headers.keys()
        if PY3:
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


@pytest.fixture
def params():
    return snug.UnorderedQueryParams(Counter({('foo', '6'): 2,
                                              ('bla', 'bar'): 1}))


@pytest.fixture
def ordered_params():
    return snug.OrderedQueryParams([
        ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
        ('foo', '6'), ('foo', '9')])


class TestAsQueryParams:

    def test_iterable(self):
        assert snug.as_queryparams((
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9')
        )) == snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9')
        ])

    def test_mapping(self):
        assert snug.as_queryparams({
            'foo': '6', 'bar': 'bla'
        }) == snug.UnorderedQueryParams(Counter({
            ('foo', '6'): 1,
            ('bar', 'bla'): 1,
        }))

    def test_counter(self):
        assert snug.as_queryparams(Counter({
            ('foo', '6'): 1,
            ('bar', 'bla'): 2,
        })) == snug.UnorderedQueryParams(Counter({
            ('bar', 'bla'): 2,
            ('foo', '6'): 1,
        }))

    def test_ordered_dict(self):
        assert snug.as_queryparams(OrderedDict([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
        ])) == snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
        ])

    def test_already_queryparams(self, params, ordered_params):
        assert snug.as_queryparams(params) == params
        assert snug.as_queryparams(ordered_params) == ordered_params


class TestUnorderedQueryParams:

    def test_empty(self):
        params = snug.UnorderedQueryParams(Counter())
        assert isinstance(params, snug.UnorderedQueryParams)
        assert len(params) == 0
        assert list(params) == []

    def test_iter(self, params):
        assert Counter(params) == Counter({
            ('foo', '6'): 2,
            ('bla', 'bar'): 1,
        })

    def test_dict_equality(self):
        param_dict = {'foo': '6', 'bar': 'bla'}
        assert snug.as_queryparams(param_dict) == param_dict

    def test_equality(self, params):
        assert params == params
        same = snug.UnorderedQueryParams(Counter({
            ('foo', '6'): 2,
            ('bla', 'bar'): 1,
        }))
        other = snug.UnorderedQueryParams(Counter({
            ('fooo', '6'): 2,
            ('bla', 'bar'): 1,
        }))

        assert params == same
        assert not params == other

        # determined by other object
        assert params == AlwaysEquals()
        assert not params == AlwaysInEquals()

    def test_inequality(self, params):
        assert not params != params
        same = snug.UnorderedQueryParams(Counter({
            ('bla', 'bar'): 1,
            ('foo', '6'): 2,
        }))
        other = snug.UnorderedQueryParams(Counter({
            ('foo', '6'): 2,
            ('bla', 'bar'): 2,
        }))

        assert params != other
        assert not params != same

        # determined by other object
        assert params == AlwaysEquals()
        assert not params == AlwaysInEquals()

    def test_add(self, params, ordered_params):
        added = params + snug.UnorderedQueryParams(Counter({
            ('foo', '6'): 1,
            ('bla', 'baz'): 1,
        }))
        assert added == snug.UnorderedQueryParams({
            ('foo', '6'): 3,
            ('bla', 'baz'): 1,
            ('bla', 'bar'): 1
        })
        assert added == params + {
            'foo': '6',
            'bla': 'baz',
        }
        assert params + AlwaysAddsToOne() == 1

        with pytest.raises(TypeError):
            params + 'foo'

    def test_len(self, params):
        assert len(params) == 3

    def test_bool(self, params):
        assert params
        assert not snug.UnorderedQueryParams({})

    def test_repr(self, params):
        rep = repr(params)
        for key, value in params:
            assert key in rep
            assert value in rep

        assert repr(snug.UnorderedQueryParams({})) == '{<empty>}'


class AlwaysAddsToOne(object):
    def __radd__(self, other):
        return 1


class TestOrderedQueryParams:

    def test_empty(self):
        params = snug.OrderedQueryParams(())
        assert isinstance(params, snug.OrderedQueryParams)
        assert len(params) == 0
        assert list(params) == []

    def test_iter(self, ordered_params):
        assert list(ordered_params) == [
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9')
        ]

    def test_seq_equality(self):
        param_seq = [('foo', '6'), ('bar', 'bla'), ('foo', '9')]
        assert snug.OrderedQueryParams(param_seq) == param_seq

    def test_equality(self, ordered_params):
        params = ordered_params
        assert params == params
        same = snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9')
        ])
        other = snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '9'), ('foo', '6')
        ])

        # true cases
        assert params == same

        # false cases
        assert not params == other

        # determined by other object
        assert params == AlwaysEquals()
        assert not params == AlwaysInEquals()

    def test_inequality(self, ordered_params):
        params = ordered_params
        assert not params != params
        same = snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9')
        ])
        other = snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '9'), ('foo', '6')
        ])

        # true cases
        assert params != other

        # false cases
        assert not params != same

        # determined by other object
        assert not params != AlwaysEquals()
        assert params != AlwaysInEquals()

    def test_len(self, ordered_params):
        assert len(ordered_params) == 5

    def test_bool(self, ordered_params):
        assert ordered_params
        assert not snug.OrderedQueryParams(())

    def test_repr(self, ordered_params):
        rep = repr(ordered_params)
        for key, value in ordered_params:
            assert key in rep
            assert value in rep

        assert repr(snug.OrderedQueryParams(())) == '[<empty>]'

    def test_add(self, ordered_params):
        added = ordered_params + snug.OrderedQueryParams([
            ('bla', 'boo'),
            ('foo', '10'),
        ])
        assert added == snug.OrderedQueryParams([
            ('foo', '6'), ('bar', 'qux'), ('bla', 'bla'),
            ('foo', '6'), ('foo', '9'), ('bla', 'boo'), ('foo', '10')
        ])
        assert ordered_params + [
            ('bla', 'boo'),
            ('foo', '10'),
        ] == added
        assert params + AlwaysAddsToOne() == 1

        with pytest.raises(TypeError):
            ordered_params + 'foo'
