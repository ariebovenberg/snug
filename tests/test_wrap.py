import json

from dataclasses import replace, dataclass

import snug

genresult = snug.utils.genresult


def test_static_wrapper():

    @snug.wrap.Static
    def jsondata(request):
        response = yield replace(request, content=json.dumps(request.content))
        return replace(response, content=json.loads(response.content))

    wrapper = jsondata.__wrap__(snug.Request('my/url/', content={'hello': 5}))
    assert next(wrapper) == snug.Request('my/url/', content='{"hello": 5}')
    response = genresult(wrapper,
                         snug.Response(200, headers={}, content=b'{"foo": 4}'))
    assert response == snug.Response(200, headers={}, content={'foo': 4})


class TestChain:

    def test_simple(self):

        @dataclass
        class Authenticator(snug.wrap.Base):
            token: str

            def prepare(self, request):
                return request.add_headers({'Authorization': self.token})

        @snug.wrap.Static
        def jsondata(request):
            response = yield replace(request,
                                     content=json.dumps(request.content))
            return replace(response, content=json.loads(response.content))

        @snug.wrap.Static
        def raise_descriptive_server_error(request):
            response = yield request
            if response.status_code == 500 and response['error']:
                raise IOError(response.content['error'])
            else:
                return response

        wrapper = snug.wrap.Chain([
            jsondata,
            Authenticator('me'),
            raise_descriptive_server_error,
        ])

        wrapped = wrapper.__wrap__(snug.Request('my/url', content={'foo': 4}))
        assert next(wrapped) == snug.Request(
            'my/url', headers={'Authorization': 'me'}, content='{"foo": 4}')
        response = genresult(wrapped, snug.Response(
            200, content=b'{"bar": 9}', headers={}))
        assert response == snug.Response(200, content={'bar': 9}, headers={})

    def test_empty(self):
        wrapper = snug.wrap.Chain()
        wrap = wrapper.__wrap__(snug.Request('my/url'))
        assert next(wrap) == snug.Request('my/url')
        assert genresult(wrap, snug.Response(201, {}, b'')) == snug.Response(
            201, {}, b'')

    def test_union(self):

        @snug.wrap.Static
        def jsondata(request):
            response = yield replace(request,
                                     content=json.dumps(request.content))
            return replace(response, content=json.loads(response.content))

        @dataclass
        class Authenticator(snug.wrap.Base):
            """an example wrapper which provides authentication"""
            token: str

            def prepare(self, request):
                return request.add_headers({'Authorization': self.token})

        wrapper = snug.wrap.Chain() | jsondata | Authenticator('me')

        assert isinstance(wrapper, snug.wrap.Chain)
        assert wrapper.wrappers == [jsondata, Authenticator('me')]
