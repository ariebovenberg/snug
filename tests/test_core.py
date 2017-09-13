from unittest import mock

import lxml
import pytest
import requests

import snug
from snug.utils import partial, compose


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
def lookup(Post):
    return Post[43]


@pytest.fixture
def filterable(Post):
    return snug.FilterableSet(
        list_load=compose(list, partial(map, Post.item_load)),
        subset_request=lambda filts: snug.Request('posts/', params=filts),
    )


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

        email = Email.item_load({'subject': 'foo'})
        assert email.subject == 'foo'

    def test_load(self):

        class User(snug.Resource):
            name = snug.Field(load='value: {}'.format)

        user = User.item_load({'name': 'foo username'})
        assert user.name == 'value: foo username'

    def test_apiname(self):

        class Comment(snug.Resource):
            is_archived = snug.Field(apiname='archived')
            user = snug.Field()

        assert Comment.is_archived.apiname == 'archived'
        assert Comment.user.apiname == 'user'


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

        User.__module__ = 'mysite'

        # instance repr
        user = User()
        assert repr(user) == '<mysite.User: foo>'
        del User.__str__
        assert repr(user) == '<mysite.User: User object>'


class TestResourceClass:

    def test_repr(self):

        class User(snug.Resource):

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        assert repr(User) == '<resource mysite.User>'

    def test_item_load(self, Post):
        api_obj = object()

        instance = Post.item_load(api_obj)
        assert isinstance(instance, Post)
        assert instance.api_obj is api_obj

    def test_indexable(self, Post):
        assert isinstance(Post, snug.Indexable)
        some_post = Post[153]
        assert isinstance(some_post, snug.Lookup)

    def test_filterable(self, Post):
        assert isinstance(Post, snug.Filterable)
        my_posts = Post[dict(author='me')]
        assert isinstance(my_posts, snug.SubSet)


class TestGetitem:

    def test_default(self):
        with pytest.raises(TypeError):
            snug.core.getitem(object(), 'foo')

    def test_mapping(self):
        assert snug.core.getitem({'foo': 4}, 'foo') == 4

    def test_xml_item(self):
        xml = lxml.objectify.fromstring('''
        <MyRoot>
          <MyParent>
            <Child1>foo</Child1>
            <Child2>bar</Child2>
          </MyParent>
        </MyRoot>
        ''')
        assert snug.core.getitem(xml, 'MyParent.Child2') == 'bar'
        assert snug.core.getitem(xml, 'MyParent').Child1 == 'foo'


def test_set(Post):
    posts = snug.Collection(
        load=compose(list, partial(map, Post.item_load)),
        request=snug.Request('posts/'),
    )
    assert snug.req(posts) == snug.Request('posts/')


def test_filterable(filterable):
    filtered = filterable[dict(archived=False, date='today')]
    assert filtered == snug.SubSet(
        source=filterable, filters={'archived': False, 'date': 'today'})
    assert snug.req(filtered) == snug.Request(
        'posts/', params=dict(archived=False, date='today'))


def test_indexable(Post):
    polls = snug.Index(
        item_load=Post.item_load,
        item_request=compose(snug.Request, 'posts/{}/'.format))
    node = polls[5]
    assert node == snug.Lookup(polls, 5)
    assert snug.req(node) == snug.Request('posts/5/')


def test_node(Post):
    latest_post = snug.Node(
        load=Post.item_load,
        request=snug.Request('posts/latest/')
    )
    assert snug.req(latest_post) == snug.Request('posts/latest/')
