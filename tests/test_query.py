import snug
from snug.utils import genresult


def test_generator_is_query():

    def mygen():
        yield
        return

    gen = mygen()
    assert isinstance(gen, snug.Query)


def test_query():

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


def test_cls_from_gen():

    @snug.query.cls_from_gen()
    def post(id: int):
        """my docstring..."""
        return (yield f'/posts/{id}/').decode('ascii')

    assert issubclass(post, snug.Query)
    assert post.__name__ == 'post'
    assert post.__doc__ == 'my docstring...'
    assert post.__module__ == 'test_query'
    assert len(post.__dataclass_fields__) == 1

    post34 = post(34)
    assert isinstance(post34, snug.Query)
    assert post34.id == 34

    resolver = iter(post34)
    assert next(resolver) == '/posts/34/'
    assert genresult(resolver, b'hello') == 'hello'
