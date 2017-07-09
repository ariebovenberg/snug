from unittest import mock

import pytest
import requests

import snug


@pytest.fixture
def resources():

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
    return snug.Api(headers={'foo': 'bar'}, resources=resources)


@pytest.fixture
def context(api):
    return snug.Context(auth=('user', 'pass'), api=api)


class TestField:

    def test_descriptor__get__(self):

        class Email(snug.Resource):
            subject = snug.Field()

        assert isinstance(Email.subject, snug.Field)

        email = snug.wrap_api_obj(Email, {'subject': 'foo'})
        assert email.subject == 'foo'

    def test_repr(self):

        class User(snug.Resource):
            name = snug.Field()

        assert repr(User.name) == '<Field "name" of {!r}>'.format(User)
        assert repr(snug.Field()) == '<Field [no name]>'

    def test_given_load_value_callable(self):

        class User(snug.Resource):
            name = snug.Field(load_value='value: {}'.format)

        user = snug.wrap_api_obj(User, {'name': 'foo username'})
        assert user.name == 'value: foo username'


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
        assert Post.fields == expect_fields

    def test_subclassing_keeps_fields(self):

        class Post(snug.Resource):
            title = snug.Field()
            body = snug.Field()
            user = snug.Field()

        class BlogPost(Post):
            url = snug.Field()

        assert BlogPost.fields == {
            'title': BlogPost.title,
            'body': BlogPost.body,
            'user': BlogPost.user,
            'url': BlogPost.url,
        }

        assert BlogPost.title.resource is BlogPost

    def test_repr(self):

        class User(snug.Resource):

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        api = snug.Api(headers={}, resources={User})
        context = snug.Context(api, auth=None)

        req_session = mock.Mock(spec=requests.Session)
        my_session = snug.Session(context, req_session=req_session)

        # class repr
        assert repr(User) == '<resource mysite.User>'

        # bound class repr
        assert repr(my_session.User) == (
            '<resource mysite.User bound to <Session(context={!r})>>'.format(
                context))

        # instance repr
        user = User()
        assert repr(user) == '<mysite.User: foo>'

        del User.__str__
        assert repr(user) == '<mysite.User: [no __str__]>'


class TestSession:

    def test_init(self, context):
        req_session = mock.Mock(spec=requests.Session)
        my_session = snug.Session(context, req_session=req_session)

        assert context.api.resources

        for resource in context.api.resources:
            bound_resource = getattr(my_session, resource.__name__)
            assert bound_resource is not resource
            assert issubclass(bound_resource, resource)
            assert bound_resource.session is my_session

        assert my_session.context is context
        assert my_session.req_session is req_session

    def test_repr(self, context):
        session = snug.Session(context=context, req_session=mock.Mock())
        assert repr(context) in repr(session)

    def test_get(self, context):
        req_session = mock.Mock(spec=requests.Session)
        session = snug.Session(context=context, req_session=req_session)

        response = session.get('/my/url/')

        req_session.get.assert_called_once_with(
            '/my/url/',
            headers=context.api.headers,
            auth=context.auth)
        assert response is req_session.get.return_value
        assert response.raise_for_status.called


def test_getitem():
    assert snug.core.getitem({'foo': 4}, 'foo') == 4


def test_wrap_api_obj(resources):
    resource = resources.pop()
    api_obj = object()

    instance = snug.wrap_api_obj(resource, api_obj)
    assert isinstance(instance, resource)
    assert instance.api_obj is api_obj
