import typing as t

import pytest

import snug


def test_as_json_response():
    raw_resp = snug.http.Response(200, b'{"foo": 4}', headers={})
    resp = snug.json.parse_response(raw_resp)
    assert isinstance(resp, snug.json.ObjectResponse)
    assert isinstance(resp, t.Mapping)
    assert resp['foo'] == 4
    assert len(resp) == 1
    assert list(resp) == ['foo']

    with pytest.raises(LookupError, match='bar'):
        resp['bar']
