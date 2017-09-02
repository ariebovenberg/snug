from unittest import mock

import lxml
import pytest
import requests

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

        email = Email.wrap({'subject': 'foo'})
        assert email.subject == 'foo'

    def test_load(self):

        class User(snug.Resource):
            name = snug.Field(load='value: {}'.format)

        user = User.wrap({'name': 'foo username'})
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

    def test_subclassing_keeps_fields(self):

        class Post(snug.Resource):
            title = snug.Field()
            body = snug.Field()
            user = snug.Field()

        class BlogPost(Post):
            url = snug.Field()

        assert BlogPost.FIELDS == {
            'title': BlogPost.title,
            'body': BlogPost.body,
            'user': BlogPost.user,
            'url': BlogPost.url,
        }

        assert BlogPost.title.resource is BlogPost
        assert BlogPost.title is not Post.title

    def test_repr(self):

        class User(snug.Resource):

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        # class repr
        assert repr(User) == '<resource mysite.User>'

        # instance repr
        user = User()
        assert repr(user) == '<mysite.User: foo>'
        del User.__str__
        assert repr(user) == '<mysite.User: User object>'

    def test_create_query_from_slices_empty(self):

        class Comment(snug.Resource):
            pass

        assert Comment[:] == snug.Set(Comment)

    def test_select_key(self):

        class User(snug.Resource):
            pass

        assert User['bob'] == snug.Node(User, 'bob')

    def test_wrap(self, resources):
        resource = resources.pop()
        api_obj = object()

        instance = resource.wrap(api_obj)
        assert isinstance(instance, resource)
        assert instance.api_obj is api_obj


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
