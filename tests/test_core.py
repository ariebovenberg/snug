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


def test_query_decorator():

    @snug.query()
    def post(id: int):
        """my docstring..."""
        return (yield f'/posts/{id}/').decode('ascii')

    assert issubclass(post, snug.Query)
    assert post.__name__ == 'post'
    assert post.__doc__ == 'my docstring...'
    assert post.__module__ == 'test_core'
    assert len(post.__dataclass_fields__) == 1

    post34 = post(34)
    assert isinstance(post34, snug.Query)
    assert post34.id == 34

    resolver = iter(post34)
    assert next(resolver) == '/posts/34/'
    assert genresult(resolver, b'hello') == 'hello'


def test_identity_pipe():
    pipe = snug.Pipe.identity('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, 'bar') == 'bar'
