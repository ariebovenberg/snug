import collections
from unittest import mock

import pytest

import omgorm as orm


@pytest.fixture
def resource(SessionSubclass):

    class Post(orm.Resource, session_cls=SessionSubclass):
        title = orm.Field()
        body = orm.Field()
        user = orm.Field()

    return Post


class TestField:

    @mock.patch.object(orm.Field, 'get_value')
    def test_field_accessor(self, value_getter, SessionSubclass):

        class Email(orm.Resource, session_cls=SessionSubclass):
            subject = orm.Field()

        assert isinstance(Email.subject, orm.Field)

        email = Email()
        assert email.subject is value_getter.return_value


class TestResource:

    def test_fields_linked_to_resource(self, SessionSubclass):

        class Post(orm.Resource, session_cls=SessionSubclass):
            title = orm.Field()
            body = orm.Field()
            user = orm.Field()

        assert Post.title.name == 'title'
        assert Post.title.resource is Post

        expect_fields = collections.OrderedDict([
            ('title', Post.title),
            ('body', Post.body),
            ('user', Post.user),
        ])
        assert Post.fields == expect_fields

    def test_from_api_obj(self, resource):
        Post = resource
        api_obj = object()

        instance = Post.wrap_api_obj(api_obj)
        assert isinstance(instance, Post)
        assert instance.api_obj is api_obj

    def test_resource_requires_session_cls(self):

        with pytest.raises(TypeError):
            class Poll(orm.Resource):
                pass


class TestSession:

    def test_resource_linked_to_session(self):

        class MySiteSession(orm.Session):
            pass

        class Post(orm.Resource, session_cls=MySiteSession):
            title = orm.Field()
            body = orm.Field()
            user = orm.Field()

        class Comment(orm.Resource, session_cls=MySiteSession):
            name = orm.Field()
            email = orm.Field()
            body = orm.Field()

        assert MySiteSession.resources == {'Post': Post, 'Comment': Comment}

    def test_resource_subclasses_per_session_instance(self, SessionSubclass):

        class Post(orm.Resource, session_cls=SessionSubclass):
            title = orm.Field()
            body = orm.Field()
            user = orm.Field()

        bobs_session = SessionSubclass(username='bob')

        assert bobs_session.Post is not Post
        assert issubclass(bobs_session.Post, Post)
        assert bobs_session.Post.session is bobs_session
