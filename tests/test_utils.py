import collections
import datetime
import inspect
from functools import reduce
from operator import attrgetter, itemgetter

import pytest

import snug

utils = snug.utils


def try_until_positive(req):
    """an example Pipe"""
    response = yield req
    while response < 0:
        response = yield 'TRY AGAIN!'
    return response


def try_until_even(req):
    """an example Pipe"""
    response = yield req
    while response % 2:
        response = yield 'NOT EVEN!'
    return response


def mymax(val):
    """an example generator function"""
    while val < 100:
        sent = yield val
        if sent > val:
            val = sent
    return val * 3


class MyMax:
    """an example generator iterable"""

    def __init__(self, start):
        self.start = start

    def __iter__(self):
        val = self.start
        while val < 100:
            sent = yield val
            if sent > val:
                val = sent
        return val * 3


def emptygen():
    if False:
        yield
    return 99


def test_isnone():
    assert not utils.notnone(None)
    assert utils.notnone(object())
    assert utils.notnone(True)
    assert utils.notnone(False)


def test_lookup_default():
    getter = utils.lookup_defaults(itemgetter('foo'), 'bla')
    assert getter({}) == 'bla'
    assert getter({'foo': 4}) == 4


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


def test_flip():

    flipped = utils.flip(int)
    assert flipped(8, '10') == 8

    other = utils.flip(int)
    assert flipped == other
    assert not flipped != other
    assert hash(flipped) == hash(other)

    assert 'int' in repr(flipped)

    assert flipped != utils.flip(divmod)
    assert not flipped == utils.flip(str)

    with pytest.raises(TypeError, match='arguments'):
        flipped(1, 2, 3)

    assert flipped != object()
    assert not flipped == object()


def test_identity():
    obj = object()
    assert utils.identity(obj) is obj


class TestCompose:

    def test_empty(self):
        obj = object()
        func = utils.compose()
        assert func(obj) is obj
        assert isinstance(func.funcs, tuple)
        assert func.funcs == ()
        assert inspect.signature(func) == inspect.signature(utils.identity)

    def test_one_func_with_multiple_args(self):
        func = utils.compose(int)
        assert func('10', base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int, )

    def test_multiple_funcs(self):
        func = utils.compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func('30', base=5) == '16'

    def test_called_as_method(self):

        class Foo:
            def __init__(self, value):
                self.value = value
            func = utils.compose(lambda x: x + 1, attrgetter('value'))

        f = Foo(4)
        assert Foo.func(f) == 5
        assert f.func() == 5

    def test_equality(self):
        func = utils.compose(int, str)
        other = utils.compose(int, str)
        assert func == other
        assert not func != other
        assert hash(func) == hash(other)

        assert not func == utils.compose(int)
        assert func != utils.compose(int)

        assert func != object()
        assert not func == object()

    def test_signature(self):

        def func1(x: str, foo, *args, c=4) -> int:
            return int(x) + foo + c

        def func2(f: int) -> str:
            return 'a' * f

        func = utils.compose(
            func2,
            lambda x: x + 4,
            func1)

        sig = inspect.signature(func)
        assert sig.parameters == inspect.signature(func1).parameters
        assert sig.return_annotation == inspect.signature(
            func2).return_annotation


class TestValmap:

    def test_empty(self):
        assert utils.valmap(int, {}) == {}

    def test_simple(self):
        assert utils.valmap(int, {'foo': '4', 'bar': 5.3}) == {
            'foo': 4, 'bar': 5}


class TestYieldMap:

    def test_empty(self):
        try:
            next(utils.yieldmap(str, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = utils.yieldmap(str, mymax(4))

        assert next(mapped) == '4'
        assert mapped.send(7) == '7'
        assert mapped.send(3) == '7'
        assert utils.genresult(mapped, 103) == 309


class TestSendMap:

    def test_empty(self):
        try:
            next(utils.sendmap(int, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = utils.sendmap(int, mymax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert utils.genresult(mapped, '104') == 312

    def test_any_iterable(self):
        mapped = utils.sendmap(int, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert utils.genresult(mapped, '104') == 312


class TestReturnMap:

    def test_empty(self):
        try:
            next(utils.returnmap(str, emptygen()))
        except StopIteration as e:
            assert e.value == '99'

    def test_simple(self):
        mapped = utils.returnmap(str, mymax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert utils.genresult(mapped, 104) == '312'

    def test_any_iterable(self):
        mapped = utils.returnmap(str, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert utils.genresult(mapped, 104) == '312'


class TestNest:

    def test_empty(self):
        try:
            next(utils.nest(emptygen(), try_until_positive))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        nested = utils.nest(mymax(4), try_until_positive)

        assert next(nested) == 4
        assert nested.send(7) == 7
        assert nested.send(6) == 7
        assert nested.send(-1) == 'TRY AGAIN!'
        assert nested.send(-4) == 'TRY AGAIN!'
        assert nested.send(0) == 7
        assert utils.genresult(nested, 102) == 306

    def test_any_iterable(self):
        nested = utils.nest(MyMax(4), try_until_positive)

        assert next(nested) == 4
        assert nested.send(7) == 7
        assert nested.send(6) == 7
        assert nested.send(-1) == 'TRY AGAIN!'
        assert nested.send(-4) == 'TRY AGAIN!'
        assert nested.send(0) == 7
        assert utils.genresult(nested, 102) == 306

    def test_accumulate(self):

        gen = reduce(utils.nest,
                     [try_until_even,
                      snug.Pipe.identity,
                      try_until_positive],
                     mymax(4))

        assert next(gen) == 4
        assert gen.send(-4) == 'TRY AGAIN!'
        assert gen.send(3) == 'NOT EVEN!'
        assert gen.send(90) == 90
        assert utils.genresult(gen, 110) == 330


def test_combined():

    gen = utils.returnmap(
        'result: {}'.format,
        utils.sendmap(
            int,
            utils.yieldmap(
                str,
                utils.nest(
                    mymax(4),
                    try_until_even))))

    assert next(gen) == '4'
    assert gen.send(3) == 'NOT EVEN!'
    assert gen.send('5') == 'NOT EVEN!'
    assert gen.send(8.4) == '8'
    assert utils.genresult(gen, 104) == 'result: 312'


def test_oneyield():

    @utils.oneyield
    def myfunc(a, b, c):
        return a + b + c

    gen = myfunc(1, 2, 3)
    assert inspect.unwrap(myfunc).__name__ == 'myfunc'
    assert inspect.isgenerator(gen)
    assert next(gen) == 6
    assert utils.genresult(gen, 9) == 9


class TestPush:

    def test_empty(self):
        obj = object()
        assert utils.push(obj) is obj

    def test_one_func(self):
        assert utils.push('6', int) == 6

    def test_multiple_funcs(self):
        assert utils.push('6', int, lambda x: x + 1, str) == '7'


class TestValFilter:

    def test_empty(self):
        assert utils.valfilter(int, {}) == {}

    def test_simple(self):
        assert utils.valfilter(lambda x: x % 2, {
            'foo': 5,
            'bar': 4,
            'baz': 3,
            'qux': 98,
        }) == {
            'foo': 5,
            'baz': 3
        }


def test_called_as_method():

    class Parent:
        @utils.called_as_method
        class Child:
            def __init__(self, parent, foo):
                self.parent, self.foo = parent, foo

    parent = Parent()

    child = parent.Child(4)
    assert child.parent is parent
    assert child.foo == 4

    child = Parent.Child(parent, 4)
    assert child.parent is parent
    assert child.foo == 4


def test_empty_mapping():
    assert isinstance(utils.EMPTY_MAPPING, collections.Mapping)
    assert utils.EMPTY_MAPPING == {}
    with pytest.raises(KeyError):
        utils.EMPTY_MAPPING['foo']

    assert len(utils.EMPTY_MAPPING) == 0
    assert list(utils.EMPTY_MAPPING) == []
    assert repr(utils.EMPTY_MAPPING) == '{}'
