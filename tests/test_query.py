import json
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
class MockSender:
    responses: field(default_factory=dict)

    def __call__(self, request):
        try:
            return next(resp for req, resp in self.responses
                        if req == request)
        except StopIteration:
            raise LookupError(f'no response for {request}')


def test_static():
    recent_posts = snug.query.Static(
        request=snug.Request('posts/recent/'),
        load=lambda d: [Post(**o) for o in d])

    assert isinstance(recent_posts, snug.Query)
    assert recent_posts.__req__() == snug.Request('posts/recent/')
    assert recent_posts.__load__([
        {'id': 4, 'title': 'hello'},
        {'id': 5, 'title': 'goodbye'},
    ]) == [
        Post(4, 'hello'),
        Post(5, 'goodbye'),
    ]


class TestQuery:

    def test_subclassing(self):

        @dataclass(frozen=True)
        class posts(snug.Query[Post]):
            count: int

            @property
            def __req__(self):
                return Request('posts/', params={'max': self.count})

            @staticmethod
            def __load__(resp):
                return [Post(**d) for d in resp]

        query = posts(count=2)
        assert isinstance(query, snug.Query)
        assert query.count == 2
        assert query.__req__ == snug.Request('posts/', params={'max': 2})
        assert query.__load__([
            {'id': 4, 'title': 'hello'},
            {'id': 5, 'title': 'goodbye'},
        ]) == [
            Post(4, 'hello'),
            Post(5, 'goodbye'),
        ]

    def test_subclassing_defaults(self):

        class posts(snug.Query):

            @property
            def __req__(self):
                return Request('posts/')

        data = [{'id': 5, 'title': 'hi'}]
        assert posts.__load__(data) == data


def test_nested():

    @dataclass(frozen=True)
    class post(snug.Query):
        """a post by its ID"""
        id: int

        def __req__(self):
            raise NotImplementedError

        @dataclass(frozen=True)
        class comments(snug.query.Nested):
            """comments for this post"""
            post:  'post'
            sort:  bool
            count: int = 15

            def __req__(self):
                raise NotImplementedError()

    assert issubclass(post.comments, snug.Query)

    post34 = post(id=34)
    post_comments = post34.comments(sort=True)

    assert isinstance(post_comments, snug.Query)
    assert post_comments == post.comments(post=post34, sort=True)


class TestForReq:

    def test_simple(self):

        def _load_posts(data):
            return [Post(**o) for o in data]

        class Foo:
            pass

        @snug.query.func(load=_load_posts)
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
        assert my_posts.__load__([
            {'id': 4, 'title': 'hello'},
            {'id': 5, 'title': 'goodbye'},
        ]) == [
            Post(4, 'hello'),
            Post(5, 'goodbye'),
        ]
        assert my_posts.__req__ == snug.Request(
            'posts/', params={'max': 10,
                              'search': 'important',
                              'archived': False})

    def test_no_defaults(self):

        @snug.query.func(load=lambda d: Post(**d))
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'posts/{id}/')

        my_post = post(id=5)
        assert my_post.__req__ == snug.Request('posts/5/')


def test_resolve():

    @snug.query.func(load=lambda d: Post(**d))
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

    sender = MockSender([
        (snug.Request('mysite.com/api/posts/4/',
                        headers={'Authorization': 'me'}),
            snug.Response(200, b'{"id": 4, "title": "my post!"}', headers={}))
    ])

    response = snug.resolve(query, api=api, sender=sender, auth='me')
    assert isinstance(response, Post)
    assert response == Post(id=4, title='my post!')


@mock.patch('urllib.request.urlopen', autospec=True,
            return_value=mock.Mock(**{
                'getcode.return_value': 200,
                'headers': {},
                'read.return_value': b'{"id": 4, "title": "another post"}'
            }))
def test_simple_resolver(urlopen):

    resolve = snug.query.simple_resolve

    @snug.query.func(load=lambda d: Post(**d))
    def post(id: int):
        """a post by its ID"""
        return snug.Request(f'mysite.com/posts/{id}/')

    post_4 = post(id=4)
    response = resolve(post_4)
    assert response == Post(id=4, title='another post')
