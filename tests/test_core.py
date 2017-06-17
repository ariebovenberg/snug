import collections

import pytest
import requests

import omgorm as orm


@pytest.fixture
def resource(SessionSubclass):

    class Post(orm.Resource, session_cls=SessionSubclass):
        title = orm.Field()
        body = orm.Field()
        user = orm.Field()

    return Post


class TestField:

    def test_descriptor__get__(self):

        class Email(orm.Resource, abstract=True):
            subject = orm.Field()

            def __getitem__(self, key):
                if key == 'subject':
                    return 'foo'

        assert isinstance(Email.subject, orm.Field)

        email = Email()
        assert email.subject == 'foo'

    def test_repr(self, SessionSubclass):

        class MyField(orm.Field):
            pass

        MyField.__module__ = 'example'

        class User(orm.Resource, session_cls=SessionSubclass):
            name = MyField()

        assert repr(User.name) == f'<example.MyField "name" of {User!r}>'
        assert repr(MyField()) == f'<example.MyField [no name]>'

    def test_given_load_callable(self):

        class User(orm.Resource, abstract=True):

            def __getitem__(self, key):
                return getattr(self, f'_{key}')

            name = orm.Field(load='value: {}'.format)

        user = User()
        user._name = 'foo username'

        assert user.name == 'value: foo username'


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

    def test_subclassing_keeps_fields(self, resource):
        Post = resource

        class BlogPost(Post):
            url = orm.Field()

        assert BlogPost.fields == collections.OrderedDict([
            ('title', BlogPost.title),
            ('body', BlogPost.body),
            ('user', BlogPost.user),
            ('url', BlogPost.url),
        ])

        assert BlogPost.title.resource is BlogPost

    def test_repr(self):

        class MySession(orm.Session):

            def __str__(self):
                return 'bla'

        MySession.__module__ = 'mysite'

        class User(orm.Resource, session_cls=MySession):
            pass

            def __str__(self):
                return 'foo'

        User.__module__ = 'mysite'

        my_session = MySession()

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

    def test_init(self, SessionSubclass):

        class Post(orm.Resource, session_cls=SessionSubclass):
            title = orm.Field()
            body = orm.Field()
            user = orm.Field()

        my_session = SessionSubclass()

        assert my_session.Post is not Post
        assert issubclass(my_session.Post, Post)
        assert my_session.Post.session is my_session
        assert isinstance(my_session.requests, requests.Session)

    def test_repr(self):

        class MySession(orm.Session):

            def __str__(self):
                return 'foo'

        MySession.__module__ = 'mysite'

        session = MySession()
        assert repr(session) == '<mysite.MySession: foo>'

        del MySession.__str__
        assert repr(session) == '<mysite.MySession: [no __str__]>'
