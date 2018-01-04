import snug
from snug.utils import genresult


def test_static():
    latest_post = snug.query.Fixed(request='/posts/latest/', load=bytes.decode)
    assert isinstance(latest_post, snug.Query)

    resolver = iter(latest_post)
    assert next(resolver) == '/posts/latest/'
    assert genresult(resolver, b'hello') == 'hello'


def test_query():

    class post(snug.Query):
        def __init__(self, id):
            self.id = id

        def __iter__(self):
            return (yield f'/posts/{self.id}/').decode('ascii')

    query = post(id=2)
    resolver = iter(query)
    assert next(resolver) == '/posts/2/'
    assert genresult(resolver, b'hello') == 'hello'


def test_base():

    class post(snug.query.Base):

        def __init__(self, id):
            self.id = id

        def _request(self):
            return f'/posts/{self.id}/'

    query = post(id=2)
    resolver = iter(query)
    assert next(resolver) == '/posts/2/'
    assert genresult(resolver, 'hello') == 'hello'


def test_called_as_method():

    class Post:
        def __init__(self, id):
            self.id = id

        @snug.query.called_as_method
        class comments(snug.Query):
            """comments for this post"""
            def __init__(self, post, sort):
                self.post, self.sort = post, sort

            def __iter__(self):
                raise NotImplementedError()

    assert issubclass(Post.comments, snug.Query)

    post34 = Post(id=34)
    post_comments = post34.comments(sort=True)

    assert isinstance(post_comments, snug.Query)
    assert post_comments.post == post34
    assert post_comments.sort is True


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


def test_cls_from_func():

    @snug.query.cls_from_func(load=bytes.decode)
    def post(id: int):
        """my docstring..."""
        return f'/posts/{id}/'

    assert post.__name__ == 'post'
    assert post.__doc__ == 'my docstring...'
    assert post.__module__ == 'test_query'
    assert issubclass(post, snug.query.Base)
    assert len(post.__dataclass_fields__) == 1

    post53 = post(53)
    assert isinstance(post53, snug.Query)
    assert post53.id == 53

    assert post53._request() == '/posts/53/'
    assert post53._parse(b'hello') == 'hello'
