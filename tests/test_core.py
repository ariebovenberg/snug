import snug


def try_shouting(req):
    """an example Pipe"""
    response = yield req
    if response == 'what?':
        response = yield req.upper()
    return response.lower()


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


def test_nested():

    @snug.nested(try_shouting)
    def convo(greeting):
        request = yield greeting
        while True:
            request = yield request + ', huh?'

    gen = convo('howdy')
    assert next(gen) == 'howdy'
    assert gen.send('foo') == 'foo, huh?'
    assert gen.send('what?') == 'FOO, HUH?'
    assert gen.send('ok') == 'ok, huh?'
