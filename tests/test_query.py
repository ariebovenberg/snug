import json
import typing as t
from operator import methodcaller, attrgetter
from unittest import mock

from dataclasses import dataclass, field
from toolz import compose

import snug
from snug import Request


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


def test_querylike():
    assert issubclass(snug.Query, snug.Querylike)


class TestQuery:

    def test_subclassing(self):

        @dataclass(frozen=True)
        class posts(snug.Query, rtype=t.List[Post]):
            count: int

            @property
            def __req__(self):
                return Request('posts/', params={'max': self.count})

        query = posts(count=2)
        assert isinstance(query, snug.Query)
        assert query.count == 2
        assert query.__rtype__ is t.List[Post]
        assert query.__req__ == snug.Request('posts/', params={'max': 2})

    def test_subclassing_defaults(self):

        class posts(snug.Query):

            @property
            def __req__(self):
                return Request('posts/')

        assert posts.__rtype__ is object

    def test_init(self):
        recent_posts = snug.Query(request=snug.Request('posts/recent/'),
                                  rtype=t.List[Post])
        assert isinstance(recent_posts, snug.Query)
        assert recent_posts.__req__ == snug.Request('posts/recent/')
        assert recent_posts.__rtype__ is t.List[Post]

    def test_init_defaults(self):
        recent_posts = snug.Query(snug.Request('posts/recent/'))
        assert recent_posts.__req__ == snug.Request('posts/recent/')
        assert recent_posts.__rtype__ is object

    def test_nested(self):

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

    def test_as_decorator_with_type(self):

        @snug.Query(Post)
        def post(id: int):
            return snug.Request(f'posts/{id}/')

        assert issubclass(post, snug.Query)
        assert post(5).__req__ == snug.Request('posts/5/')
        assert post.__rtype__ is Post

    def test_as_decorator_no_type(self):

        @snug.Query()
        def post(id: int):
            return snug.Request(f'posts/{id}/')

        assert issubclass(post, snug.Query)
        assert post(5).__req__ == snug.Request('posts/5/')
        assert post.__rtype__ is object

    def test_as_decorator_no_call(self):

        @snug.Query
        def post(id: int):
            return snug.Request(f'posts/{id}/')

        assert issubclass(post, snug.Query)
        assert post(5).__req__ == snug.Request('posts/5/')
        assert post.__rtype__ is object


class TestFromRequestFunc:

    def test_simple(self):

        class Foo:
            pass

        @snug.query.from_request_func(rtype=t.List[Post])
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

        @snug.query.from_request_func(rtype=Post)
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'posts/{id}/')

        my_post = post(id=5)
        assert my_post.__req__ == snug.Request('posts/5/')


def test_resolve():

    loaders = {Post: lambda data: Post(**data)}.__getitem__

    @snug.Query(Post)
    def post(id: int):
        """a post by its ID"""
        return snug.Request(f'posts/{id}/')

    query = post(id=4)

    api = snug.Api(
        prepare=methodcaller('add_prefix', 'mysite.com/api/'),
        parse=compose(
            json.loads,
            methodcaller('decode'),
            attrgetter('content')),
        add_auth=lambda req, auth: req.add_headers({'Authorization': 'me'}),
    )

    client = MockClient([
        (snug.Request('mysite.com/api/posts/4/',
                        headers={'Authorization': 'me'}),
            snug.Response(200, b'{"id": 4, "title": "my post!"}', headers={}))
    ])

    response = snug.resolve(query, api=api, client=client, auth='me',
                            loaders=loaders)
    assert isinstance(response, Post)
    assert response == Post(id=4, title='my post!')


@mock.patch('snug.http.send', autospec=True,
            return_value=snug.Response(
                200, b'{"id": 4, "title": "another post"}', headers={}))
def test_simple_resolver(http_send):

    resolve = snug.query.simple_resolve

    @snug.query.from_request_func(rtype=Post)
    def post(id: int):
        """a post by its ID"""
        return snug.Request(f'mysite.com/posts/{id}/')

    post_4 = post(id=4)
    response = resolve(post_4)
    http_send.assert_called_once_with(mock.ANY,
                                      Request('https://mysite.com/posts/4/'))
    assert response == Post(id=4, title='another post')
