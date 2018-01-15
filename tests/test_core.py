import asyncio
import inspect
import pickle
import types

import pytest

import snug


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


def test_generator_is_query():

    def mygen():
        yield
        return

    gen = mygen()
    assert isinstance(gen, snug.Query)


@snug.querytype()
def simplequery(a: str):
    """simply query bound to module"""
    return (yield a)


class TestQueryType:

    def test_pickleable_instances(self):
        query = simplequery(5)
        assert pickle.loads(pickle.dumps(query)) == query

    def test_related(self):

        class Parent:
            def __init__(self, foo):
                self.foo = foo

            @snug.querytype(related=True)
            def query(parent, a: int):
                return (yield parent.foo + a)

        child = Parent(3).query(4)
        assert isinstance(child, Parent.query)

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

        changed = query.replace(b=9)
        assert changed == myquery(4, 9, d=6, foo=10)


@pytest.mark.asyncio
async def test_execute_async():

    async def sender(req):
        await asyncio.sleep(0)
        if not req.endswith('/'):
            return 'redirect:' + req + '/'
        elif req == '/posts/latest/':
            return 'hello world'

    def myquery():
        response = yield '/posts/latest'
        while response.startswith('redirect:'):
            response = yield response[9:]
        return response.upper()

    query = myquery()
    assert await snug.execute_async(query, sender=sender) == 'HELLO WORLD'
