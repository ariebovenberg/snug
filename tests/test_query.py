import json
import typing as t
from operator import methodcaller, attrgetter
from unittest import mock

from dataclasses import dataclass, field
from toolz import compose

import snug
from snug import Request, Response


@dataclass
class Post:
    id:    int
    title: str


@dataclass
class Comment:
    id:   int
    text: str


@dataclass
class MockClient:
    responses: field(default_factory=dict)


@snug.http.send.register(MockClient)
def _send_with_test_client(client, request):
    try:
        return next(resp for req, resp in client.responses
                    if req == request)
    except StopIteration:
        raise LookupError(f'no response for {request}')


class TestQuery:

    def test_subclassing(self):

        @dataclass(frozen=True)
        class posts(snug.Query, rtype=t.List[Post]):
            count: int

            @property
            def __req__(self):
                return snug.Request('posts/', params={'max': self.count})

        query = posts(count=2)
        assert isinstance(query, snug.query.Query)
        assert query.count == 2
        assert query.__rtype__ == t.List[Post]
        assert query.__req__ == snug.Request('posts/', params={'max': 2})

    def test_init(self):
        recent_posts = snug.Query(request=snug.Request('posts/recent/'),
                                  rtype=t.List[Post])
        assert isinstance(recent_posts, snug.Query)

    def test_binding(self):

        @dataclass(frozen=True)
        class post(snug.Query, rtype=Post):
            """a post by its ID"""
            id: int

            @dataclass(frozen=True)
            class comments(snug.Query, rtype=t.List[Comment]):
                """comments for this post"""
                post:  'post'
                sort:  bool
                count: int = 15

        assert 'post.comments' in repr(post.comments)
        assert issubclass(post.comments, snug.Query)

        post34 = post(id=34)
        post_comments = post34.comments(sort=True)

        assert isinstance(post_comments, snug.Query)
        assert post_comments == post.comments(post=post34, sort=True)


class TestFromFunc:

    def test_simple(self):

        class Foo:
            pass

        @snug.query.from_func(rtype=t.List[Post])
        def posts(count: int, search: str='', archived: bool=False):
            """my docstring..."""
            return snug.Request(
                'posts/',
                params={'max': count, 'search': search, 'archived': archived})

        assert posts.__name__ == 'posts'
        assert posts.__doc__ == 'my docstring...'
        assert posts.__module__ == Foo.__module__
        assert issubclass(posts, snug.Query)
        assert len(posts.__dataclass_fields__) == 3

        my_posts = posts(count=10, search='important')
        assert isinstance(my_posts, snug.Query)
        assert my_posts.count == 10
        assert my_posts.search == 'important'
        assert my_posts.__rtype__ == t.List[Post]
        assert my_posts.__req__ == snug.Request(
            'posts/', params={'max': 10,
                              'search': 'important',
                              'archived': False})

    def test_no_defaults(self):

        @snug.query.from_func(rtype=Post)
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'posts/{id}/')

        my_post = post(id=5)
        assert my_post.__req__ == snug.Request('posts/5/')


class TestResolve:

    def test_resolve(self):

        @snug.query.from_func(rtype=Post)
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'posts/{id}/')

        query = post(id=4)

        def load(dtype, data):
            assert dtype is Post
            return dtype(**data)

        api = snug.Api(
            prepare=methodcaller('add_prefix', 'mysite.com/api/'),
            parse=compose(
                json.loads,
                methodcaller('decode'),
                attrgetter('content'))
        )

        client = MockClient([
            (snug.Request('mysite.com/api/posts/4/',
                          headers={'Authorization': 'me'}),
             snug.Response(200, b'{"id": 4, "title": "my post!"}', headers={}))
        ])
        auth = methodcaller('add_headers', {'Authorization': 'me'})

        response = snug.resolve(query, api=api, client=client, auth=auth,
                                load=load)
        assert isinstance(response, Post)
        assert response == Post(id=4, title='my post!')

    @mock.patch('snug.http.send', autospec=True,
                return_value=snug.Response(
                    200, b'{"id": 4, "title": "another post"}', headers={}))
    def test_defaults(self, http_send):

        @snug.query.from_func(rtype=Post)
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'/posts/{id}/')

        post_4 = post(id=4)
        response = snug.resolve(post_4)
        assert response == Post(id=4, title='another post')


def test_simple_json_api():
    api = snug.query.simple_json_api
    assert api.prepare(Request('my/url/')) == Request('https://my/url/')
    assert api.parse(Response(200, b'{"foo": 4}', {})) == {'foo': 4}


def test_simple_loader():
    load = snug.load.simple_loader
    loaded = load(Post, {'id': 9, 'title': 'hello'})
    assert isinstance(loaded, Post)
    assert loaded == Post(id=9, title='hello')


