import json

import pytest
from dataclasses import replace

import snug


@pytest.fixture
def jsonwrapper():

    @snug.wrap.Fixed
    def jsondata(request):
        response = yield replace(request, data=json.dumps(request.data))
        return json.loads(response.data)

    return jsondata


@pytest.fixture
def response():
    return snug.Response(200, b'{"id": 5, "title": "hello"}')
