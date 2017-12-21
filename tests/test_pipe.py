import json
from dataclasses import dataclass

import snug

genresult = snug.utils.genresult


class TestChain:

    def test_simple(self):

        @dataclass
        class Authenticator(snug.Pipe):
            token: str

            def __call__(self, request):
                response = yield request.add_headers(
                    {'Authorization': self.token})
                if response.status_code == 403:
                    raise ValueError('authentication failed!')
                return response

        @snug.pipe.Parser
        def raise_on_server_error(response):
            if response.status_code == 500:
                raise IOError(response.data.decode('ascii'))
            else:
                return response

        @snug.pipe.Preparer
        def set_content_length(request):
            assert isinstance(request.data, bytes)
            return request.add_headers({
                'Content-Length': len(request.data)})

        pipeline = snug.pipe.Chain(
            snug.lib.jsonpipe,
            Authenticator('me'),
            set_content_length,
            raise_on_server_error,
        )

        pipe = pipeline(snug.Request('my/url', {'foo': 4}))
        assert next(pipe) == snug.Request(
            'my/url', b'{"foo": 4}', headers={
                'Authorization': 'me',
                'Content-Length': 10,
            })
        response = genresult(pipe, snug.Response(200, b'{"bar": 9}'))
        assert response == {'bar': 9}

    def test_empty(self):
        pipe = snug.pipe.Chain()(snug.Request('my/url'))
        assert next(pipe) == snug.Request('my/url')
        assert genresult(pipe, snug.Response(201, {}, b'')) == snug.Response(
            201, {}, b'')

    def test_union(self, jsonwrapper):

        @dataclass
        class Authenticator(snug.pipe.Base):
            """an example pipe which provides authentication"""
            token: str

            def _prepare(self, request):
                return request.add_headers({'Authorization': self.token})

        pipeline = snug.pipe.Chain() | jsonwrapper | Authenticator('me')

        assert isinstance(pipeline, snug.pipe.Chain)
        assert pipeline.stages == (jsonwrapper, Authenticator('me'))


def test_identity():
    pipe = snug.pipe.identity(snug.Request('my/url'))
    assert next(pipe) == snug.Request('my/url')
    resp = snug.Response(200)
    assert genresult(pipe, resp) == resp


def test_base():

    class MyAPI(snug.pipe.Base):
        pass

    pipe = MyAPI()(snug.Request('my/url'))
    assert next(pipe) == snug.Request('my/url')
    resp = snug.Response(200)
    assert genresult(pipe, resp) == resp


def test_preparer(response):

    @snug.pipe.Preparer
    def add_auth_header(request):
        return request.add_headers({'Authorization': 'me'})

    pipe = add_auth_header(snug.Request('my/url'))
    prepared = next(pipe)
    assert prepared == snug.Request('my/url', headers={'Authorization': 'me'})
    # responses are unmodified
    assert response == genresult(pipe, response)


def test_parser(response):

    @snug.pipe.Parser
    def parse_json(response):
        return json.loads(response.data)

    pipe = parse_json(snug.Request('my/url'))
    assert next(pipe) == snug.Request('my/url')
    assert genresult(pipe, snug.Response(200, b'{"foo": 5}')) == {'foo': 5}
