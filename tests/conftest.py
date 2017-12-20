import asyncio
import json
from dataclasses import replace, dataclass

import pytest

import snug


@pytest.fixture
def Post():
    """an example dataclass"""

    @dataclass
    class Post:
        id:    int
        title: str

    return Post


@pytest.fixture
def jsonwrapper():

    def jsondata(request):
        response = yield replace(request, data=json.dumps(request.data))
        return json.loads(response.data)

    return jsondata


@pytest.fixture
def response():
    return snug.Response(200, b'{"id": 5, "title": "hello"}')


@pytest.fixture
def query(Post):
    return snug.query.Fixed(request=snug.Request('posts/recent/'),
                            load=lambda r: [Post(**o)
                                            for o in json.loads(r.data)])


@pytest.fixture
def async_resolver():
    """a simple HTTP resolver for posts/recent/"""

    async def _sender(request):
        await asyncio.sleep(0)
        assert request.url == 'posts/recent/'
        return snug.Response(200, json.dumps([
            {
                "id": 5,
                "title": "hello world"
            },
            {
                "id": 6,
                "title": "goodbye"
            },
        ]).encode('ascii'))

    return _sender


@pytest.fixture
def resolver():
    """a simple HTTP resolver for posts/recent/"""

    def _sender(request):
        assert request.url == 'posts/recent/'
        return snug.Response(200, json.dumps([
            {
                "id": 5,
                "title": "hello world"
            },
            {
                "id": 6,
                "title": "goodbye"
            },
        ]).encode('ascii'))

    return _sender
