import json
import typing as t
from operator import methodcaller, attrgetter
from unittest import mock

from dataclasses import dataclass, field, replace
from toolz import compose

import snug
from snug.utils import genresult


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

    resolver = recent_posts.__resolve__()
    assert next(resolver) == snug.Request('posts/recent/')
    assert genresult(resolver, [
        {'id': 4, 'title': 'hello'},
        {'id': 5, 'title': 'goodbye'},
    ]) == [
        Post(4, 'hello'),
        Post(5, 'goodbye'),
    ]


class TestQuery:

    def test_subclassing(self):

        @dataclass
        class posts(snug.Query[t.List[Post]]):
            count: int

            def __resolve__(self):
                return [
                    Post(**d)
                    for d in (yield snug.Request('posts/',
                                                 params={'max': self.count}))
                ]

        query = posts(count=2)
        assert isinstance(query, snug.Query)
        assert query.count == 2

        resolver = query.__resolve__()
        assert next(resolver) == snug.Request('posts/', params={'max': 2})
        assert genresult(resolver, [
            {'id': 4, 'title': 'hello'},
            {'id': 5, 'title': 'goodbye'},
        ]) == [
            Post(4, 'hello'),
            Post(5, 'goodbye'),
        ]


def test_nested():

    @dataclass(frozen=True)
    class post(snug.Query):
        """a post by its ID"""
        id: int

        def __resolve__(self):
            raise NotImplementedError

        @dataclass(frozen=True)
        class comments(snug.query.Nested):
            """comments for this post"""
            post:  'post'
            sort:  bool
            count: int = 15

            def __resolve__(self):
                raise NotImplementedError()

    assert issubclass(post.comments, snug.Query)

    post34 = post(id=34)
    post_comments = post34.comments(sort=True)

    assert isinstance(post_comments, snug.Query)
    assert post_comments == post.comments(post=post34, sort=True)


def test_wrapped():

    @dataclass
    class JsonApi(snug.query.Wrapper):
        host: str

        def __wrap__(self, request):
            response = yield request.add_prefix(self.host)
            return json.loads(response)

    api = JsonApi('mysite.com/')

    @dataclass
    class post(snug.Query):
        id: int

        def __resolve__(self):
            return Post(**(yield snug.Request(f'posts/{self.id}/')))

    wrapped = snug.query.Wrapped(post(4), wrapper=api)

    resolver = wrapped.__resolve__()
    request = next(resolver)
    assert request == snug.Request('mysite.com/posts/4/')
    response = genresult(resolver, '{"id": 4, "title": "hi"}')
    assert response == Post(id=4, title='hi')


def test_gen():

    @snug.query.gen
    def posts(count: int, search: str='', archived: bool=False):
        """my docstring..."""
        response = yield snug.Request(
            'posts/',
            params={'max': count, 'search': search, 'archived': archived})
        return [Post(**obj) for obj in response]

    assert issubclass(posts, snug.Query)
    assert posts.__name__ == 'posts'
    assert posts.__doc__ == 'my docstring...'
    assert posts.__module__ == 'test_query'
    assert len(posts.__dataclass_fields__) == 3

    my_posts = posts(count=10, search='important')
    assert isinstance(my_posts, snug.Query)
    assert my_posts.count == 10
    assert my_posts.search == 'important'

    resolver = my_posts.__resolve__()
    request = next(resolver)
    assert request == snug.Request(
        'posts/', params={'max': 10,
                          'search': 'important',
                          'archived': False})
    response = genresult(resolver, [
        {'id': 4, 'title': 'hello'},
        {'id': 5, 'title': 'goodbye'},
    ])
    assert response == [
        Post(4, 'hello'),
        Post(5, 'goodbye'),
    ]


class TestFunc:

    def test_simple(self):

        @snug.query.request
        def posts(count: int, search: str='', archived: bool=False):
            """my docstring..."""
            return snug.Request(
                'posts/',
                params={'max': count, 'search': search, 'archived': archived})

        assert posts.__name__ == 'posts'
        assert posts.__doc__ == 'my docstring...'
        assert posts.__module__ == 'test_query'
        assert issubclass(posts, snug.Query)
        assert len(posts.__dataclass_fields__) == 3

        my_posts = posts(count=10, search='important')
        assert isinstance(my_posts, snug.Query)
        assert my_posts.count == 10
        assert my_posts.search == 'important'

        resolver = my_posts.__resolve__()
        assert next(resolver) == snug.Request(
            'posts/', params={
                'max': 10,
                'search': 'important',
                'archived': False
            })
        assert genresult(resolver, [
            {'id': 4, 'title': 'hello'},
            {'id': 5, 'title': 'goodbye'},
        ]) == [
            {'id': 4, 'title': 'hello'},
            {'id': 5, 'title': 'goodbye'},
        ]

    def test_no_defaults(self):

        @snug.query.request
        def post(id: int):
            """a post by its ID"""
            return snug.Request(f'posts/{id}/')

        my_post = post(id=5)
        assert next(my_post.__resolve__()) == snug.Request('posts/5/')


def test_resolve():

    @snug.query.gen
    def post(id: int):
        """a post by its ID"""
        return Post(**(yield snug.Request(f'posts/{id}/')))

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

    @snug.query.gen
    def post(id: int):
        """a post by its ID"""
        return Post(**(yield snug.Request(f'mysite.com/posts/{id}/')))

    post_4 = post(id=4)
    response = resolve(post_4)
    assert response == Post(id=4, title='another post')
