import snug
from snug.utils import genresult


def test_execute():
    sender = {
        '/posts/latest': 'redirect:/posts/latest/',
        '/posts/latest/': 'redirect:/posts/december/',
        '/posts/december/': b'hello world'
    }.__getitem__

    class MyQuery:
        def __resolve__(self):
            redirect = yield '/posts/latest'
            redirect = yield redirect.split(':')[1]
            response = yield redirect.split(':')[1]
            return response.decode('ascii')

    assert snug.execute(sender, MyQuery()) == 'hello world'


def test_nest():

    def get_post_text(id):
        post_info = yield f'posts/{id}'
        text = yield post_info['text_url']
        return text.decode()

    def follow_redirects(req):
        response = yield req
        while isinstance(response, str) and response.startswith('redirect:'):
            response = yield response[9:]
        return response

    nested = snug.nest(get_post_text(id=4), follow_redirects)

    assert next(nested) == 'posts/4'
    assert nested.send('redirect:/posts/4/') == '/posts/4/'
    assert nested.send({'text_url': '/download/a3fbe/'}) == '/download/a3fbe/'
    assert genresult(nested, b'hello') == 'hello'
