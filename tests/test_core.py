from unittest import mock

import pytest
import requests

import snug


@pytest.fixture
def resource(SessionSubclass):

    class Post(snug.Resource, session_cls=SessionSubclass):
        title = snug.Field()
        body = snug.Field()
        user = snug.Field()

    return Post


@pytest.fixture
def req_session():
    return requests.Session()


class TestField:

    def test_descriptor__get__(self):

        class Email(snug.Resource, abstract=True):
            subject = snug.Field()

            def __getitem__(self, key):
                if key == 'subject':
                    return 'foo'

        assert isinstance(Email.subject, snug.Field)

        email = Email()
        assert email.subject == 'foo'

    def test_repr(self, SessionSubclass):

        class MyField(snug.Field):
            pass

        MyField.__module__ = 'example'

        class User(snug.Resource, session_cls=SessionSubclass):
            name = MyField()

        assert repr(User.name) == '<example.MyField "name" of {!r}>'.format(
            User)
        assert repr(MyField()) == '<example.MyField [no name]>'

    def test_given_load_callable(self):

        class User(snug.Resource, abstract=True):

            def __getitem__(self, key):
                return getattr(self, '_' + key)

            name = snug.Field(load='value: {}'.format)

        user = User()
        user._name = 'foo username'

        assert user.name == 'value: foo username'


class TestResource:

    def test_fields_linked_to_resource(self, SessionSubclass):

        class Post(snug.Resource, session_cls=SessionSubclass):
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

    def test_from_api_obj(self, resource):
        Post = resource
        api_obj = object()

        instance = Post.wrap_api_obj(api_obj)
        assert isinstance(instance, Post)
        assert instance.api_obj is api_obj

    def test_resource_requires_session_cls(self):

        with pytest.raises(TypeError):
            class Poll(snug.Resource):
                pass

    def test_subclassing_keeps_fields(self, resource):
        Post = resource

        class BlogPost(Post):
            url = snug.Field()

        assert BlogPost.fields == {
            'title': BlogPost.title,
            'body': BlogPost.body,
            'user': BlogPost.user,
            'url': BlogPost.url,
        }

        assert BlogPost.title.resource is BlogPost

    def test_repr(self, req_session):

        class MySession(snug.Session):

            def __str__(self):
                return 'bla'

        MySession.__module__ = 'mysite'

        class User(snug.Resource, session_cls=MySession):
            pass

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        my_session = MySession(req_session=req_session)

        # class repr
        assert repr(User) == '<resource mysite.User>'

        # bound class repr
        assert repr(my_session.User) == (
            '<resource mysite.User bound to <mysite.MySession: bla>>')

        # instance repr
        user = User()
        assert repr(user) == '<mysite.User: foo>'

        del User.__str__
        assert repr(user) == '<mysite.User: [no __str__]>'


class TestSession:

    def test_resource_linked_to_session(self):

        class MySiteSession(snug.Session):
            pass

        class Post(snug.Resource, session_cls=MySiteSession):
            title = snug.Field()
            body = snug.Field()
            user = snug.Field()

        class Comment(snug.Resource, session_cls=MySiteSession):
            name = snug.Field()
            email = snug.Field()
            body = snug.Field()

        assert MySiteSession.resources == {'Post': Post, 'Comment': Comment}

    def test_init(self, SessionSubclass, req_session):

        class Post(snug.Resource, session_cls=SessionSubclass):
            title = snug.Field()
            body = snug.Field()
            user = snug.Field()

        my_session = SessionSubclass(req_session=req_session)

        assert my_session.Post is not Post
        assert issubclass(my_session.Post, Post)
        assert my_session.Post.session is my_session

        assert my_session.req_session is req_session

    def test_repr(self, req_session):

        class MySession(snug.Session):

            def __str__(self):
                return 'foo'

        MySession.__module__ = 'mysite'

        session = MySession(req_session=req_session)
        assert repr(session) == '<mysite.MySession: foo>'

        del MySession.__str__
        assert repr(session) == '<mysite.MySession: [no __str__]>'

    def test_get(self, req_session):

        session = snug.Session(req_session=req_session)

        with mock.patch.object(session, 'req_session') as req_session:
            response = session.get('/my/url/', foo='bar')

        req_session.get.assert_called_once_with('/my/url/', foo='bar')
        assert response is req_session.get.return_value
        assert response.raise_for_status.called
