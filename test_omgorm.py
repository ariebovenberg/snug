import pytest
import collections

import omgorm as orm


@pytest.fixture
def session_class():
    class MySiteSession(orm.Session):
        pass

    return MySiteSession


class TestResource:

    def test_fields_linked_to_resource(self, session_class):

        class Post(orm.Resource, session_cls=session_class):
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

        assert Post.session_cls is MySiteSession
        assert Comment.session_cls is MySiteSession

        assert MySiteSession.resources == {'Post': Post, 'Comment': Comment}
