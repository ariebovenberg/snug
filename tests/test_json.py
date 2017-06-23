import pytest

import snug


class TestResource:

    def test_get_field_value(self):

        class Post(snug.json.Resource, abstract=True):
            pass

        post = Post.wrap_api_obj({
            'title': 'my post',
            'user': {
                'name': 'bob'
            }
        })
        assert post['title'] == 'my post'
        assert post['user', 'name'] == 'bob'

        with pytest.raises(KeyError):
            post['body']

        with pytest.raises(TypeError):
            post[0]
