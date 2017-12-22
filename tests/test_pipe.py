import snug

genresult = snug.utils.genresult


class TestChain:

    def test_simple(self):

        def ascii_encoded(req):
            return (yield req.encode('ascii')).decode('ascii')

        def simon_says(req):
            return (yield f'simon says: "{req}"')

        def shout(req):
            return (yield req).upper()

        chain = snug.pipe.Chain(shout, simon_says, ascii_encoded)

        pipe = chain('knock knock')
        assert next(pipe) == b'simon says: "knock knock"'
        assert genresult(pipe, b"who\'s there?") == "WHO'S THERE?"

    def test_empty(self):
        pipe = snug.pipe.Chain()('foo')
        assert next(pipe) == 'foo'
        assert genresult(pipe, 'bar') == 'bar'

    def test_union(self):

        def ascii_encoded(req):
            return (yield req.encode('ascii')).decode('ascii')

        def loud(req):
            return (yield req.upper()).lower()

        pipeline = snug.pipe.Chain() | ascii_encoded | loud

        assert isinstance(pipeline, snug.pipe.Chain)
        assert pipeline.stages == (ascii_encoded, loud)


def test_identity():
    pipe = snug.pipe.identity('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, 'bar') == 'bar'


def test_base():

    class MyAPI(snug.pipe.Base):
        pass

    pipe = MyAPI()('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, 'bar') == 'bar'


def test_preparer():

    @snug.pipe.Preparer
    def shout(req):
        return req.upper()

    pipe = shout('foo')
    assert next(pipe) == 'FOO'
    assert genresult(pipe, 'bar') == 'bar'


def test_parser():

    @snug.pipe.Parser
    def ascii_decode(resp):
        return resp.decode('ascii')

    pipe = ascii_decode('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, b'bar') == 'bar'
