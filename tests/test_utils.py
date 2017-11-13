from operator import itemgetter

import pytest

import snug
from dataclasses import dataclass

utils = snug.utils


class TestOnlyOne:

    def test_ok(self):
        assert utils.onlyone([1]) == 1

    def test_too_many(self):
        with pytest.raises(ValueError, match='expected 1'):
            utils.onlyone([1, 2])

    def test_too_few(self):
        with pytest.raises(ValueError, match='expected 1'):
            utils.onlyone([])


def test_replace():

    @dataclass
    class Comment:
        title: str
        body: str

    comment = Comment('my comment', 'blabla')
    newcomment = utils.replace(comment, body='actual comment')
    assert newcomment == Comment('my comment', 'actual comment')


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
