import asyncio
import json
import typing as t
from unittest import mock
from dataclasses import dataclass

import pytest

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


@pytest.fixture
def sender():
    """a simple HTTP sender for Post resources"""

    def _sender(request):
        # resource/id/ -> (resource, id)
        resource, id_ = request.url.strip('/').split('/')
        assert resource == 'posts'
        return snug.Response(200, json.dumps({
            "id": int(id_),
            "title": "hello world"
        }).encode('ascii'))

    return _sender


@pytest.fixture
def async_sender():
    """a simple HTTP sender for Post resources"""

    async def _sender(request):
        await asyncio.sleep(0)
        # resource/id/ -> (resource, id)
        resource, id_ = request.url.strip('/').split('/')
        assert resource == 'posts'
        return snug.Response(200, json.dumps({
            "id": int(id_),
            "title": "hello world"
        }).encode('ascii'))

    return _sender


@pytest.fixture
def post_by_id():

    @snug.query.gen
    def post(id: int):
        """query to get a post by it's ID"""
        return Post(**json.loads((yield snug.Request(f'/posts/{id}/')).data))

    return post


def test_static():
    recent_posts = snug.query.Fixed(
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


def test_wrapped(jsonwrapper):

    @dataclass
    class post(snug.Query):
        id: int

        def __resolve__(self):
            return Post(**(yield snug.Request(
                f'posts/{self.id}/', {'foo': 4})))

    wrapped = snug.query.Wrapped(post(4), wrapper=jsonwrapper)

    resolve = wrapped.__resolve__()
    request = next(resolve)
    assert request == snug.Request('posts/4/', '{"foo": 4}')
    response = genresult(resolve,
                         snug.Response(200, '{"id": 4, "title": "hi"}'))
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


class TestRequester:

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


def test_resolve(sender, post_by_id):
    response = snug.resolve(sender, post_by_id(5))
    assert response == Post(id=5, title='hello world')


@pytest.mark.asyncio
async def test_resolve_async(async_sender, post_by_id):
    response = await snug.resolve_async(async_sender, post_by_id(4))
    assert response == Post(id=4, title='hello world')


def test_build_resolver(jsonwrapper):

    def sender(request):
        assert 'Authorization' in request.headers
        assert request.url == 'posts/99/'
        return snug.Response(200, b'{"id": 99, "title": "hello"}')

    @snug.query.gen
    def post(id: int):
        """get a post by id"""
        return Post(**(yield snug.Request(f'posts/{id}/')))

    resolver = snug.build_resolver(
        ('username', 'hunter2'),
        sender=sender,
        wrapper=jsonwrapper,
        authenticator=snug.Request.add_basic_auth,
    )
    response = resolver(post(99))
    assert response == Post(id=99, title='hello')


@pytest.mark.asyncio
async def test_build_async_resolver(jsonwrapper):

    async def sender(request):
        assert 'Authorization' in request.headers
        assert request.url == 'posts/99/'
        await asyncio.sleep(0)
        return snug.Response(200, b'{"id": 99, "title": "hello"}')

    @snug.query.gen
    def post(id: int):
        """get a post by id"""
        return Post(**(yield snug.Request(f'posts/{id}/')))

    resolver = snug.build_async_resolver(
        ('username', 'hunter2'),
        sender=sender,
        wrapper=jsonwrapper,
        authenticator=snug.Request.add_basic_auth,
    )
    response = await resolver(post(99))
    assert response == Post(id=99, title='hello')


@mock.patch('urllib.request.urlopen', autospec=True,
            return_value=mock.Mock(**{
                'getcode.return_value': 200,
                'headers': {},
                'read.return_value': b'{"id": 4, "title": "another post"}'
            }))
def test_simple_resolver(urlopen):

    resolve = snug.query.simple_resolver(auth=('foo', 'bar'))

    @snug.query.gen
    def post(id: int):
        """a post by its ID"""
        return Post(**(yield snug.Request(f'https://localhost/posts/{id}/')))

    post_4 = post(id=4)
    response = resolve(post_4)
    assert response == Post(id=4, title='another post')
