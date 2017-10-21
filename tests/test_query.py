import typing as t

from dataclasses import dataclass

import snug


@dataclass
class Post:
    id:            int
    title:         str
    archived:      bool
    comment_count: int


@dataclass
class Comment:
    id:   int
    text: str


def test_subclassing():

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


def test_init():
    recent_posts = snug.Query(request=snug.Request('posts/recent/'),
                              rtype=t.List[Post])
    assert isinstance(recent_posts, snug.Query)


def test_binding():

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
