from unittest import mock

import lxml
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
    """an API with mock functionality"""
    return snug.Api(create_url=mock.Mock(),
                    headers={},
                    parse_response=mock.Mock(),
                    resources=resources)


@pytest.fixture
def session(api, auth):
    """a session with mock functionality"""
    return snug.Session(
        api, auth=auth, req_session=mock.Mock(spec=requests.Session))


@pytest.fixture
def auth():
    return ('user', 'pass')


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

    def test_load(self):

        class User(snug.Resource):
            name = snug.Field(load='value: {}'.format)

        user = snug.wrap_api_obj(User, {'name': 'foo username'})
        assert user.name == 'value: foo username'

    def test_apiname(self):

        class Comment(snug.Resource):
            is_archived = snug.Field(apiname='archived')
            user = snug.Field()

        assert Comment.is_archived.apiname == 'archived'
        assert Comment.user.apiname == 'user'


class TestBoundResource:

    @mock.patch('requests.Session')
    def test_repr(self, _, api):

        class User(snug.Resource):
            pass

        User.__module__ = 'mysite'

        api.resources.add(User)
        my_session = snug.Session(api)

        # bound class repr
        assert repr(my_session.User) == '<bound resource mysite.User>'


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

    def test_create_query_from_slices_one_key(self):

        class User(snug.Resource):
            pass

        assert User['bob'] == snug.Node(User, 'bob')


class TestSession:

    def test_init(self, auth, api):
        req_session = mock.Mock(spec=requests.Session)
        my_session = snug.Session(api,
                                  auth=auth,
                                  req_session=req_session)

        assert api.resources

        for resource in api.resources:
            bound_resource = getattr(my_session, resource.__name__)
            assert bound_resource is not resource
            assert issubclass(bound_resource, resource)
            assert bound_resource.session is my_session

        assert my_session.api is api
        assert my_session.auth is auth
        assert my_session.req_session is req_session

    def test_init_defaults(self, api):
        session = snug.Session(api)
        assert session.api == api
        assert session.auth is None
        assert isinstance(session.req_session, requests.Session)

    def test_get(self, session):
        Post = next(r for r in session.api.resources if r.__name__ == 'Post')
        response = session.req_session.get.return_value

        query = snug.Node(Post, '1')
        result = session.get(query)
        assert result is session.api.parse_response.return_value

        session.req_session.get.assert_called_once_with(
            session.api.create_url(query),
            headers=session.api.headers,
            auth=session.auth)
        assert response.raise_for_status.called


class TestGetitem:

    def test_default(self):
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


def test_wrap_api_obj(resources):
    resource = resources.pop()
    api_obj = object()

    instance = snug.wrap_api_obj(resource, api_obj)
    assert isinstance(instance, resource)
    assert instance.api_obj is api_obj
