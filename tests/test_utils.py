import operator
import functools
import typing as t

import pytest

from snug import utils


def _example_func(*args, **kwargs):
    return args, kwargs


class TestPartial:

    def test_is_subclass(self):
        assert issubclass(utils.partial, functools.partial)

    def test_placeholder(self):
        func = utils.partial(_example_func, ..., ..., 'foo', ...,
                             bla='bing', another='thing')

        args, kwargs = func(1, 2, 3, another='thing2')

        assert args == (1, 2, 'foo', 3)
        assert kwargs == {'bla': 'bing', 'another': 'thing2'}

    def test_no_placeholders(self):
        func = utils.partial(_example_func, 'foo', 5)
        args, kwargs = func(10)

        assert args == ('foo', 5, 10)
        assert not kwargs


class TestCompose:

    def test_empty(self):
        func = utils.compose()
        assert func('abc') == 'abc'

    def test_multiple(self):
        func = utils.compose(
            str,
            utils.partial(operator.add, 5),
            utils.partial(operator.truediv, 1)
        )
        assert func(4) == '5.25'


class TestSlots:

    def test_slots(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            body:      str = ''
            archived:  bool = False

        assert isinstance(Post, type)
        assert Post.__bases__ == (utils.Slots, )
        assert Post.__slots__ == {'title': str,
                                  'author_id': int,
                                  'body': str,
                                  'archived': bool}

        post = Post('hello', 4, 'my message', True)

        assert isinstance(post, Post)
        assert post.title == 'hello'
        assert post.author_id == 4
        assert post.body == 'my message'
        assert post.archived is True

        # can't set invalid attributes
        with pytest.raises(AttributeError, match='date'):
            post.date = 'foo'

    def test_eq(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            archived:  bool

        post1 = Post('hello', 6, False)
        post2 = Post('hello', 0, False)
        post3 = Post('hello', 6, False)

        assert post1 == post3
        assert not post1 != post3
        assert post1 != post2
        assert not post1 == post2

    def test_init(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            body:      str = '<no message>'
            archived:  bool = False

        post = Post('hello', author_id=5, archived=True)
        assert post == Post('hello', 5, '<no message>', True)

        # duplicate arg
        with pytest.raises(TypeError, match='author_id'):
            post = Post('hi', 9, author_id=4, archived=False)

        # missing arg
        with pytest.raises(TypeError, match='author_id'):
            post = Post('hello', archived=False)

    def test_repr(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            archived:  bool

        post = Post('hello world', author_id=4, archived=False)

        assert repr(post) == (
            f'Post(title=\'hello world\', author_id=4, archived=False)')

    def test_empty(self):

        class User(utils.Slots):
            pass

        assert not User.__slots__

    def test_mixes_with_abstract_base_classes(self):

        from collections.abc import Sequence, Callable, Collection

        class Email(Callable, Sequence, utils.Slots):
            sender:     str
            recipients: t.List[str]
            body:       str = ''

            def __getitem__(self, index):
                return self.recipients[index]

            def __len__(self):
                return len(self.recipients)

            def __call__(self):
                return 'sent email!'

        email = Email('my.email@test.com', recipients=[
            'bob@acme.com', 'wilma@company.org'
        ])

        assert isinstance(email, Collection)
        assert isinstance(email, Sequence)
        assert isinstance(email, Callable)
        assert len(email) == 2
        assert email() == 'sent email!'

    def test_override_method(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            archived:  bool = False

            def __init__(self, title, *args, **kwargs):
                super().__init__(title.upper(), *args, **kwargs)

        post = Post('Hello', author_id=5)

        assert post.title == 'HELLO'
        assert post.author_id == 5

    def test_astuple(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            body:      str = '<no message>'
            archived:  bool = False

        post = Post('hi', author_id=9)

        assert post._astuple() == ('hi', 9, '<no message>', False)

    def test_asdict(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            body:      str = '<no message>'
            archived:  bool = False

        post = Post('hi', author_id=9)

        assert post._asdict() == {
            'title': 'hi',
            'author_id': 9,
            'body': '<no message>',
            'archived': False
        }

    def test_replace(self):

        class Post(utils.Slots):
            title:     str
            author_id: int
            body:      str = '<no message>'
            archived:  bool = False

        post = Post('hi', author_id=9)
        newpost = post._replace(author_id=12, body='real message')
        assert newpost != post
        assert newpost == Post('hi', 12, 'real message', False)

