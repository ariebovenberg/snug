import typing as t
import datetime
from operator import itemgetter
from unittest import mock
from dataclasses import field

import pytest

import snug

utils = snug.utils


def test_str_repr():

    class User(utils.StrRepr):

        def __str__(self):
            return 'foo'

    # instance repr
    user = User()
    assert repr(user) == '<User: foo>'
    del User.__str__
    assert repr(user) == '<User: User object>'


class TestApply:

    def test_defaults(self):

        def func():
            return 'foo'

        assert utils.apply(func) == 'foo'

    def test_simple(self):

        def func(a, b, c):
            return a + b + c

        assert utils.apply(func, (1, 2), {'c': 5}) == 8


def test_isnone():
    assert not utils.notnone(None)
    assert utils.notnone(object())
    assert utils.notnone(True)
    assert utils.notnone(False)


def test_lookup_default():
    getter = utils.lookup_defaults(itemgetter('foo'), 'bla')
    assert getter({}) == 'bla'
    assert getter({'foo': 4}) == 4


def test_skipnone():
    myfunc = utils.skipnone(str.strip)
    assert myfunc('  blabla   \n') == 'blabla'
    assert myfunc(None) is None


class TestParseIso8601:

    def test_with_timezone(self):
        parsed = utils.parse_iso8601('2012-02-27T13:08:00+0100')
        assert parsed == datetime.datetime(
            2012, 2, 27, 13, 8,
            tzinfo=datetime.timezone(datetime.timedelta(hours=1)))

    def test_no_timezone(self):
        parsed = utils.parse_iso8601('2014-06-10T17:25:29Z')
        assert parsed == datetime.datetime(2014, 6, 10, 17, 25, 29)


class TestGenreturn:

    def test_ok(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        assert utils.genresult(gen, 0) == 'foo'

    def test_no_return(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        with pytest.raises(TypeError, match='did not return'):
            utils.genresult(gen, 1)


class TestFuncToFields:

    def test_no_fields(self):

        def myfunc():
            pass

        assert utils.func_to_fields(myfunc) == []

    def test_simple_args(self):

        def myfunc(foo: int, bar: float):
            pass

        assert utils.func_to_fields(myfunc) == [
            ('foo', int, mock.ANY),
            ('bar', float, mock.ANY),
        ]

    def test_missing_annotation(self):

        def myfunc(foo: int, bar):
            pass

        assert utils.func_to_fields(myfunc) == [
            ('foo', int, mock.ANY),
            ('bar', t.Any, mock.ANY),
        ]

    def test_keyword_only(self):

        def myfunc(foo: int, *, bar: float):
            pass

        with pytest.raises(TypeError, match='keyword.only'):
            utils.func_to_fields(myfunc)

    def test_varargs(self):

        def myfunc(foo: int, *bar: float):
            pass

        with pytest.raises(TypeError, match='varargs'):
            utils.func_to_fields(myfunc)

    def test_varkw(self):

        def myfunc(foo: int, **bar: float):
            pass

        with pytest.raises(TypeError, match='varkw'):
            utils.func_to_fields(myfunc)

    def test_defaults(self):

        _missing = field().default

        def myfunc(foo: int, bar=9, qux: str=''):
            pass

        fields = utils.func_to_fields(myfunc)
        assert fields == [
            ('foo', int, mock.ANY),
            ('bar', t.Any, mock.ANY),
            ('qux', str, mock.ANY),
        ]
        assert [f.default for _, _, f in fields] == [
            _missing,
            9,
            ''
        ]
