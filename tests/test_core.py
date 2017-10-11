from unittest import mock

import lxml
import pytest
import requests
from dataclasses import dataclass

import snug


@pytest.fixture
def resources():
    """a set of two resources"""

    class Post(snug.Resource):
        title = snug.Field()
        body = snug.Field()
        user = snug.Field()

    class Comment(snug.Resource):
        name = snug.Field()
        email = snug.Field()
        body = snug.Field()

    return {Post, Comment}


@pytest.fixture
def Post():

    class Post(snug.Resource):
        title = snug.Field()
        body = snug.Field()
        user = snug.Field()

    return Post


@pytest.fixture
def set_(Post):
    return snug.AtomicSet(type=Post, request=snug.Request('posts/recent/'))


@pytest.fixture
def item(Post):

    @dataclass(frozen=True)
    class post(snug.Item, type=Post):
        id: int

        def __request__(self):
            return snug.Request(f'posts/{self.id}/')

    return post(32)


@pytest.fixture
def api(resources):
    """an API with mock functionality"""
    return snug.Api(headers={}, resources=resources)


@pytest.fixture
def session(api, auth):
    """a session with mock functionality"""
    return snug.Session(
        api, auth=auth, req_session=mock.Mock(spec=requests.Session))


@pytest.fixture
def auth():
    """dummy authentication credential tuple"""
    return ('user', 'pass')


class TestField:

    def test_descriptor__get__(self):

        class Email(snug.Resource):
            subject = snug.Field()

        assert isinstance(Email.subject, snug.Field)

        email = Email.load({'subject': 'foo'})
        assert email.subject == 'foo'

        broken_email = Email.load({'sender': 'me'})

        with pytest.raises(KeyError):
            broken_email.subject

    def test_load(self):

        class User(snug.Resource):
            name = snug.Field(load='value: {}'.format)

        user = User.load({'name': 'foo username'})
        assert user.name == 'value: foo username'

    def test_apiname(self):

        class Comment(snug.Resource):
            is_archived = snug.Field(apiname='archived')
            user = snug.Field()

        assert Comment.is_archived.apiname == 'archived'
        assert Comment.user.apiname == 'user'

    def test_load_optional(self):

        class User(snug.Resource):
            nickname = snug.Field(optional=True)

        user = User.load(dict(name='bob'))
        assert user.nickname is None

    @mock.patch('snug.core.getitem', autospec=True,
                return_value=['foo', 'bar'])
    def test_list(self, getitem):

        class User(snug.Resource):
            hobbies = snug.Field(list=True)

        User = User.load(object())

        assert User.hobbies == getitem.return_value

        getitem.assert_called_once_with(mock.ANY, 'hobbies', aslist=True)


class TestResource:

    def test_fields_linked_to_resource(self):

        class Post(snug.Resource):
            title = snug.Field()
            body = snug.Field()
            user = snug.Field()

        assert Post.title.name == 'title'
        assert Post.title.resource is Post

        expect_fields = {
            'title': Post.title,
            'body': Post.body,
            'user': Post.user,
        }
        assert Post.FIELDS == expect_fields

    def test_repr(self):

        class User(snug.Resource):

            def __str__(self):
                return 'foo'

        # instance repr
        user = User()
        assert repr(user) == '<User: foo>'
        del User.__str__
        assert repr(user) == '<User: User object>'


class TestResourceClass:

    def test_repr(self):

        class User(snug.Resource):

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        assert repr(User) == '<resource mysite.User>'

    def test_load(self, Post):
        api_obj = object()

        instance = Post.load(api_obj)
        assert isinstance(instance, Post)
        assert instance.api_obj is api_obj


class TestGetitem:

    def test_default(self):
        with pytest.raises(TypeError):
            snug.core.getitem(object(), 'foo')

    def test_mapping(self):
        assert snug.core.getitem({'foo': 4}, 'foo', False) == 4

        with pytest.raises(LookupError, match='blabla'):
            snug.core.getitem({'foo': 4}, 'blabla', True)

    def test_xml_item(self):
        xml = lxml.etree.fromstring('''
        <MyRoot>
          <MyParent>
            <Child1>foo</Child1>
            <Child1>bar</Child1>
          </MyParent>
        </MyRoot>
        ''')
        assert snug.core.getitem(xml, 'MyParent/Child1[1]/text()',
                                 aslist=False) == 'foo'
        assert snug.core.getitem(xml, 'MyParent/Child1/text()',
                                 aslist=True) == ['foo', 'bar']

        with pytest.raises(LookupError, match='blabla'):
            snug.core.getitem(xml, 'MyParent.blabla', aslist=True)


def test_set(set_, Post):
    assert isinstance(set_, snug.Requestable)
    assert set_.type is Post

    posts = snug.load(set_, [
        {'title': 'hello',
         'body': 'message1',
         'user': 3},
        {'title': 'hello again',
         'body': 'message2',
         'user': 4},
    ])
    assert len(posts) == 2
    assert all(isinstance(p, Post) for p in posts)


def test_item(item, Post):
    assert item.type is Post
    assert isinstance(item, snug.Requestable)

    post = snug.load(item, {'title': 'hello', 'body': 'message', 'author': 1})
    assert isinstance(post, Post)
