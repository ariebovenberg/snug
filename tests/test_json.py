import pytest

import snug


class TestParseResponse:

    def test_object(self):
        raw_resp = snug.http.Response(200, b'{"foo": 4}', headers={})
        resp = snug.json.parse_response(raw_resp)
        assert isinstance(resp, snug.Response)
        assert resp['foo'] == 4
        assert len(resp) == 1
        assert list(resp) == ['foo']

        with pytest.raises(LookupError, match='bar'):
            resp['bar']

    def test_list(self):
        raw_resp = snug.http.Response(200, b'[1, 3, "foo"]', headers={})
        resp = snug.json.parse_response(raw_resp)
        assert isinstance(resp, snug.Response)
        assert resp[2] == 'foo'
        assert len(resp) == 3
        assert list(resp) == [1, 3, 'foo']

        with pytest.raises(LookupError):
            resp[4]
