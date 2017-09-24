from unittest import mock

import lxml
import pytest
import requests

import snug
from snug.utils import compose, identity


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

        @snug.Connection
        def tags(lookup):
            return snug.Collection(
                load=identity,
                request=snug.Request(f'posts/{lookup.key}/tags/'),
            )

        @staticmethod
        def item_request(key):
            return snug.Request(f'posts/{key}/')

    return Post


@pytest.fixture
def lookup(Post):
    return Post[43]


@pytest.fixture
def filterable(Post):
    return snug.FilterableSet(
        load=Post.load,
        subset_request=lambda filts: snug.Request('posts/', params=filts),
    )


@pytest.fixture
def indexable(Post):
    return snug.Index(
        load=Post.load,
        item_request=compose(snug.Request, 'posts/{}/'.format))


@pytest.fixture
def queryable(Post):
    return snug.QueryableSet(
        request=snug.Request('posts'),
        load=Post.load,
        item_request=compose(snug.Request, 'posts/{}/'.format),
        subset_request=lambda f: snug.Request('posts/', params=f),
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
        assert snug.core.getitem({'foo': 4}, 'foo', False) == 4

        with pytest.raises(LookupError, match='blabla'):
            snug.core.getitem({'foo': 4}, 'blabla', True)

    def test_xml_item(self):
        xml = lxml.objectify.fromstring('''
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


def test_set(Post):
    posts = snug.Collection(
        load=Post.load,
        request=snug.Request('posts/'),
    )
    assert snug.req(posts) == snug.Request('posts/')


def test_filterable(filterable):
    filtered = filterable[dict(archived=False, date='today')]
    assert filtered == snug.SubSet(
        source=filterable, filters={'archived': False, 'date': 'today'})


def test_indexable(indexable):
    node = indexable[5]
    assert node == snug.Lookup(indexable, 5)


def test_queryable(queryable):
    assert isinstance(queryable[5], snug.Lookup)
    assert isinstance(queryable[dict(search='foo')], snug.SubSet)


def test_node(Post):
    latest_post = snug.Node(
        load=Post.load,
        request=snug.Request('posts/latest/')
    )
    assert snug.req(latest_post) == snug.Request('posts/latest/')


def test_lookup(lookup):
    assert snug.req(lookup) == lookup.index.item_request(lookup.key)
    assert lookup.tags == lookup.index.item_connections['tags'](lookup)

    with pytest.raises(AttributeError):
        lookup.non_existant_connection
