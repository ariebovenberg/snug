import inspect
import types
from functools import reduce

import pytest

from snug import gentools, utils


def try_until_positive(req):
    """an example Pipe"""
    response = yield req
    while response < 0:
        response = yield 'NOT POSITIVE!'
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


def test_reusable():

    class mywrapper:
        def __init__(self, func):
            self.__wrapped__ = func
            self.__signature__ = inspect.signature(func).replace(
                return_annotation=str)

        def __call__(self, *args, **kwargs):
            inner = self.__wrapped__(*args, **kwargs)
            yield str(next(inner))

    @gentools.reusable
    @mywrapper  # dummy to test combining with other decorators
    def gentype(a: int, b: float, *cs, d, e=5, **fs):
        """my docstring"""
        return (yield sum([a, b, *cs, d, e, a]))

    gentype.__qualname__ = 'mymodule.gentype'

    assert issubclass(gentype, gentools.Generable)
    assert isinstance(inspect.unwrap, types.FunctionType)
    gentype.__name__ == 'myfunc'
    gentype.__doc__ == 'my docstring'
    gentype.__module__ == 'test_core'
    gen = gentype(4, 5, d=6, foo=10)

    assert {'a', 'b', 'cs', 'd', 'e', 'fs'} < set(dir(gen))
    assert gen.a == 4
    assert gen.b == 5
    assert gen.cs == ()
    assert gen.e == 5
    assert gen.fs == {'foo': 10}

    assert next(iter(gen)) == '24'

    othergen = gentype(4, b=5, d=6, e=5, foo=10)
    assert gen == othergen
    assert not gen != othergen
    assert hash(gen) == hash(othergen)

    assert repr(gen) == ("mymodule.gentype("
                         "a=4, b=5, cs=(), d=6, e=5, fs={'foo': 10})")

    assert not gen == gentype(3, 4, 5, d=10)
    assert gen != gentype(1, 2, d=7)

    assert not gen == object()
    assert gen != object()

    changed = gen.replace(b=9)
    assert changed == gentype(4, 9, d=6, foo=10)


class TestGenreturn:

    def test_ok(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        assert gentools.genresult(gen, 0) == 'foo'

    def test_no_return(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        with pytest.raises(TypeError, match='did not return'):
            gentools.genresult(gen, 1)


class TestYieldMap:

    def test_empty(self):
        try:
            next(gentools.yieldmap(str, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = gentools.yieldmap(str, mymax(4))

        assert next(mapped) == '4'
        assert mapped.send(7) == '7'
        assert mapped.send(3) == '7'
        assert gentools.genresult(mapped, 103) == 309


class TestSendMap:

    def test_empty(self):
        try:
            next(gentools.sendmap(int, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = gentools.sendmap(int, mymax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.genresult(mapped, '104') == 312

    def test_any_iterable(self):
        mapped = gentools.sendmap(int, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.genresult(mapped, '104') == 312


class TestReturnMap:

    def test_empty(self):
        try:
            next(gentools.returnmap(str, emptygen()))
        except StopIteration as e:
            assert e.value == '99'

    def test_simple(self):
        mapped = gentools.returnmap(str, mymax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.genresult(mapped, 104) == '312'

    def test_any_iterable(self):
        mapped = gentools.returnmap(str, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.genresult(mapped, 104) == '312'


class TestNest:

    def test_empty(self):
        try:
            next(gentools.nest(emptygen(), try_until_positive))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        nested = gentools.nest(mymax(4), try_until_positive)

        assert next(nested) == 4
        assert nested.send(7) == 7
        assert nested.send(6) == 7
        assert nested.send(-1) == 'NOT POSITIVE!'
        assert nested.send(-4) == 'NOT POSITIVE!'
        assert nested.send(0) == 7
        assert gentools.genresult(nested, 102) == 306

    def test_any_iterable(self):
        nested = gentools.nest(MyMax(4), try_until_positive)

        assert next(nested) == 4
        assert nested.send(7) == 7
        assert nested.send(6) == 7
        assert nested.send(-1) == 'NOT POSITIVE!'
        assert nested.send(-4) == 'NOT POSITIVE!'
        assert nested.send(0) == 7
        assert gentools.genresult(nested, 102) == 306

    def test_accumulate(self):

        gen = reduce(gentools.nest,
                     [try_until_even, try_until_positive],
                     mymax(4))

        assert next(gen) == 4
        assert gen.send(-4) == 'NOT POSITIVE!'
        assert gen.send(3) == 'NOT EVEN!'
        assert gen.send(90) == 90
        assert gentools.genresult(gen, 110) == 330


def test_combined():

    gen = gentools.returnmap(
        'result: {}'.format,
        gentools.sendmap(
            int,
            gentools.yieldmap(
                str,
                gentools.nest(
                    mymax(4),
                    try_until_even))))

    assert next(gen) == '4'
    assert gen.send(3) == 'NOT EVEN!'
    assert gen.send('5') == 'NOT EVEN!'
    assert gen.send(8.4) == '8'
    assert gentools.genresult(gen, 104) == 'result: 312'


def test_oneyield():

    @gentools.oneyield
    def myfunc(a, b, c):
        return a + b + c

    gen = myfunc(1, 2, 3)
    assert inspect.unwrap(myfunc).__name__ == 'myfunc'
    assert inspect.isgenerator(gen)
    assert next(gen) == 6
    assert gentools.genresult(gen, 9) == 9


def test_nested():
    decorated = gentools.nested(try_until_even, try_until_positive)(mymax)

    gen = decorated(4)
    assert next(gen) == 4
    assert gen.send(8) == 8
    assert gen.send(9) == 'NOT EVEN!'
    assert gen.send(2) == 8
    assert gen.send(-1) == 'NOT POSITIVE!'
    assert gentools.genresult(gen, 102) == 306


def test_yieldmapped():
    decorated = gentools.yieldmapped(str, lambda x: x * 2)(mymax)

    gen = decorated(5)
    assert next(gen) == '10'
    assert gen.send(2) == '10'
    assert gen.send(9) == '18'
    assert gen.send(12) == '24'
    assert gentools.genresult(gen, 103) == 309


def test_sendmapped():
    decorated = gentools.sendmapped(lambda x: x * 2, int)(mymax)

    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(5.3) == 10
    assert gen.send(9) == 18
    assert gentools.genresult(gen, '103') == 618


def test_returnmapped():
    decorated = gentools.returnmapped(lambda s: s.center(5), str)(mymax)
    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(9) == 9
    assert gentools.genresult(gen, 103) == ' 309 '


def test_combining_decorators():
    decorators = utils.compose(
        gentools.returnmapped('result: {}'.format),
        gentools.sendmapped(int),
        gentools.yieldmapped(str),
        gentools.nested(try_until_even),
    )
    decorated = decorators(mymax)
    gen = decorated(4)
    assert next(gen) == '4'
    assert gen.send('6') == '6'
    assert gen.send('5') == 'NOT EVEN!'
    assert gentools.genresult(gen, '104') == 'result: 312'

    assert inspect.unwrap(decorated) is mymax
