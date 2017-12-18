import json
from dataclasses import replace

import pytest

import snug


@pytest.fixture
def jsonwrapper():

    def jsondata(request):
        response = yield replace(request, data=json.dumps(request.data))
        return json.loads(response.data)

    return jsondata


@pytest.fixture
def response():
    return snug.Response(200, b'{"id": 5, "title": "hello"}')
