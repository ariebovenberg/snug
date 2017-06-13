import collections

import omgorm as orm


def test_model_fields_definition():

    class Post(orm.Resource):
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
    assert Post._fields == expect_fields
