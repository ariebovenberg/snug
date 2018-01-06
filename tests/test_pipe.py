import snug

genresult = snug.utils.genresult


def test_identity():
    pipe = snug.pipe.identity('foo')
    assert next(pipe) == 'foo'
    assert genresult(pipe, 'bar') == 'bar'
