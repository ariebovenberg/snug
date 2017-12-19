import asyncio
import json
from dataclasses import dataclass

import pytest

import snug

genresult = snug.utils.genresult


class TestChain:

    def test_simple(self):

        @dataclass
        class Authenticator(snug.Wrapper):
            token: str

            def __call__(self, request):
                response = yield request.add_headers(
                    {'Authorization': self.token})
                if response.status_code == 403:
                    raise ValueError('authentication failed!')
                return response

        @snug.wrap.Parser
        def raise_on_server_error(response):
            if response.status_code == 500:
                raise IOError(response.data.decode('ascii'))
            else:
                return response

        @snug.wrap.Preparer
        def set_content_length(request):
            assert isinstance(request.data, bytes)
            return request.add_headers({
                'Content-Length': len(request.data)})

        wrapper = snug.wrap.Chain(
            snug.wrap.jsondata,
            Authenticator('me'),
            set_content_length,
            raise_on_server_error,
        )

        wrapped = wrapper(snug.Request('my/url', {'foo': 4}))
        assert next(wrapped) == snug.Request(
            'my/url', b'{"foo": 4}', headers={
                'Authorization': 'me',
                'Content-Length': 10,
            })
        response = genresult(wrapped, snug.Response(200, b'{"bar": 9}'))
        assert response == {'bar': 9}

    def test_empty(self):
        wrap = snug.wrap.Chain()(snug.Request('my/url'))
        assert next(wrap) == snug.Request('my/url')
        assert genresult(wrap, snug.Response(201, {}, b'')) == snug.Response(
            201, {}, b'')

    def test_union(self, jsonwrapper):

        @dataclass
        class Authenticator(snug.wrap.Base):
            """an example wrapper which provides authentication"""
            token: str

            def _prepare(self, request):
                return request.add_headers({'Authorization': self.token})

        wrapper = snug.wrap.Chain() | jsonwrapper | Authenticator('me')

        assert isinstance(wrapper, snug.wrap.Chain)
        assert wrapper.wrappers == (jsonwrapper, Authenticator('me'))


def test_identity():
    wrap = snug.wrap.identity(snug.Request('my/url'))
    assert next(wrap) == snug.Request('my/url')
    resp = snug.Response(200)
    assert genresult(wrap, resp) == resp


def test_base():

    class MyAPI(snug.wrap.Base):
        pass

    wrap = MyAPI()(snug.Request('my/url'))
    assert next(wrap) == snug.Request('my/url')
    resp = snug.Response(200)
    assert genresult(wrap, resp) == resp


def test_preparer(response):

    @snug.wrap.Preparer
    def add_auth_header(request):
        return request.add_headers({'Authorization': 'me'})

    wrap = add_auth_header(snug.Request('my/url'))
    prepared = next(wrap)
    assert prepared == snug.Request('my/url', headers={'Authorization': 'me'})
    # responses are unmodified
    assert response == genresult(wrap, response)


def test_parser(response):

    @snug.wrap.Parser
    def parse_json(response):
        return json.loads(response.data)

    wrap = parse_json(snug.Request('my/url'))
    assert next(wrap) == snug.Request('my/url')
    assert genresult(wrap, snug.Response(200, b'{"foo": 5}')) == {
        'foo': 5}


def test_sender(jsonwrapper):

    def _sender(request):
        return snug.Response(
            404,
            data='{{"error": "{} not found"}}'.format(request.url)
            .encode('ascii'))

    sender = snug.wrap.Sender(_sender, wrapper=jsonwrapper)
    response = sender(snug.Request('my/url', {'foo': 4}))
    assert response == {'error': 'my/url not found'}


@pytest.mark.asyncio
async def test_async_sender(jsonwrapper):

    async def _sender(request):
        await asyncio.sleep(0)
        return snug.Response(
            404,
            data='{{"error": "{} not found"}}'.format(request.url)
            .encode('ascii'))

    sender = snug.wrap.AsyncSender(_sender, wrapper=jsonwrapper)
    response = await sender(snug.Request('my/url', {'foo': 4}))
    assert response == {'error': 'my/url not found'}


class TestJsonData:

    def test_simple(self):
        wrap = snug.wrap.jsondata(
            snug.Request('my/url', {'foo': 6}))
        assert next(wrap) == snug.Request('my/url', b'{"foo": 6}')
        response = genresult(wrap, snug.Response(404, b'{"error": 9}'))
        assert response == {'error': 9}

    def test_no_data(self):
        wrap = snug.wrap.jsondata(snug.Request('my/url'))
        assert next(wrap) == snug.Request('my/url')
        assert genresult(wrap, snug.Response(404)) is None
