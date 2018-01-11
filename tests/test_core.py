import inspect
import types

import snug
from snug.utils import genresult


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
    return val


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


def test_nested():
    decorated = snug.nested(try_until_even)(mymax)

    gen = decorated(4)
    assert next(gen) == 4
    assert gen.send(8) == 8
    assert gen.send(9) == 'NOT EVEN!'
    assert gen.send(2) == 8
    assert genresult(gen, 102) == 102


def test_yieldmapped():
    decorated = snug.yieldmapped(str)(mymax)

    gen = decorated(5)
    assert next(gen) == '5'
    assert gen.send(2) == '5'
    assert genresult(gen, 103) == 103


def test_sendmapped():
    decorated = snug.sendmapped(int)(mymax)

    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(5.3) == 5
    assert genresult(gen, '103') == 103


def test_returnmapped():
    decorated = snug.returnmapped(str)(mymax)
    gen = decorated(5)
    assert next(gen) == 5
    assert genresult(gen, 103) == '103'


def test_query_class():

    class post(snug.Query):
        def __init__(self, id):
            self.id = id

        def __iter__(self):
            return (yield f'/posts/{self.id}/').decode('ascii')

    query = post(id=2)
    gen = iter(query)
    assert isinstance(query, snug.Query)
    assert next(gen) == '/posts/2/'
    assert genresult(gen, b'hello') == 'hello'


def test_generator_is_query():

    def mygen():
        yield
        return

    gen = mygen()
    assert isinstance(gen, snug.Query)


class TestQueryType:

    def test_example(self):

        class mywrapper:
            def __init__(self, func):
                self.__wrapped__ = func
                self.__signature__ = inspect.signature(func).replace(
                    return_annotation=str)

            def __call__(self, *args, **kwargs):
                inner = self.__wrapped__(*args, **kwargs)
                yield str(next(inner))

        @snug.querytype()
        @mywrapper
        def myquery(a: int, b: float, *cs, d, e=5, **fs):
            """my docstring"""
            return (yield sum([a, b, *cs, d, e, a]))

        myquery.__qualname__ = 'mymodule.myquery'

        assert issubclass(myquery, snug.Query)
        assert isinstance(inspect.unwrap, types.FunctionType)
        myquery.__name__ == 'myfunc'
        myquery.__doc__ == 'my docstring'
        myquery.__module__ == 'test_core'
        query = myquery(4, 5, d=6, foo=10)

        assert {'a', 'b', 'cs', 'd', 'e', 'fs'} < set(dir(query))
        assert query.a == 4
        assert query.b == 5
        assert query.cs == ()
        assert query.e == 5
        assert query.fs == {'foo': 10}

        assert next(iter(query)) == '24'

        otherquery = myquery(4, b=5, d=6, e=5, foo=10)
        assert query == otherquery
        assert not query != otherquery
        assert hash(query) == hash(otherquery)

        assert repr(query) == ("mymodule.myquery("
                               "a=4, b=5, cs=(), d=6, e=5, fs={'foo': 10})")

        assert not query == myquery(3, 4, 5, d=10)
        assert query != myquery(1, 2, d=7)

        assert not query == object()
        assert query != object()


def test_identity_pipe():
    pipe = snug.Pipe.identity('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, 'bar') == 'bar'
