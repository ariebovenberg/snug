import snug

from snug.utils import genresult


def try_until_even(req):
    """an example Pipe"""
    response = yield req
    while response % 2:
        response = yield 'NOT EVEN!'
    return response


def mymax(val):
    """an example generator function"""
    while val < 100:
        sent = yield val
        if sent > val:
            val = sent
    return val


class TestExec:

    def test_query(self):
        sender = {
            '/posts/latest': 'redirect:/posts/latest/',
            '/posts/latest/': 'redirect:/posts/december/',
            '/posts/december/': b'hello world'
        }.__getitem__

        class MyQuery:
            def __iter__(self):
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
    decorated = snug.nested(try_until_even)(mymax)

    gen = decorated(4)
    assert next(gen) == 4
    assert gen.send(8) == 8
    assert gen.send(9) == 'NOT EVEN!'
    assert gen.send(2) == 8
    assert genresult(gen, 102) == 102


def test_yieldmapped():
    decorated = snug.yieldmapped(str)(mymax)

    gen = decorated(5)
    assert next(gen) == '5'
    assert gen.send(2) == '5'
    assert genresult(gen, 103) == 103


def test_sendmapped():
    decorated = snug.sendmapped(int)(mymax)

    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(5.3) == 5
    assert genresult(gen, '103') == 103


def test_returnmapped():
    decorated = snug.returnmapped(str)(mymax)
    gen = decorated(5)
    assert next(gen) == 5
    assert genresult(gen, 103) == '103'
