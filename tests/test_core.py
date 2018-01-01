from functools import reduce

import snug
from snug.utils import genresult


class TestExec:

    def test_resolvable(self):
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

        assert snug.exec(sender, MyQuery()) == 'hello world'

    def test_generator(self):

        def mygen(id, encoding):
            post_info = yield f'/posts/{id}/'
            text = yield post_info['text_url']
            return text.decode(encoding)

        sender = {
            '/posts/4/': {'text_url': 'downloads/2fe/'},
            'downloads/2fe/': b'hello',
        }.__getitem__

        assert snug.exec(sender, mygen(4, encoding='ascii'))


class TestNested:

    def test_example(self):

        def get_post_text(id, encoding):
            post_info = yield f'posts/{id}'
            text = yield post_info['text_url']
            return text.decode(encoding)

        def follow_redirects(req):
            response = yield req
            while isinstance(response, str) and response.startswith(
                    'redirect:'):
                response = yield response[9:]
            return response

        nested = snug.nested(get_post_text, follow_redirects)
        resolver = nested(id=4, encoding='ascii')

        assert next(resolver) == 'posts/4'
        assert resolver.send('redirect:/posts/4/') == '/posts/4/'
        assert resolver.send(
            {'text_url': '/download/a3fbe/'}) == '/download/a3fbe/'
        assert genresult(resolver, b'hello') == 'hello'

    def test_identity(self):

        def shout(req):
            response = yield req
            if response == 'cant hear you':
                response = yield req.upper()
            return response.lower()

        nested = reduce(snug.nested, [snug.pipe.identity,
                                      shout,
                                      snug.pipe.identity,
                                      snug.pipe.identity])

        gen = nested('my request!')
        assert next(gen) == 'my request!'
        assert gen.send('cant hear you') == 'MY REQUEST!'
        assert genresult(gen, 'HELLO') == 'hello'
