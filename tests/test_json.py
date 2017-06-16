import omgorm as orm


class TestField:

    def test_get_value(self, SessionSubclass):

        class Post(orm.Resource, session_cls=SessionSubclass):
            title = orm.json.Field()

        post = Post.wrap_api_obj({'title': 'hello'})

        assert post.title == 'hello'
