import collections

import pytest

import snug


def test_identity():
    obj = object()
    assert snug._identity(obj) is obj


class TestCompose:

    def test_one_func_with_multiple_args(self):
        func = snug._compose(int)
        assert func('10', base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int, )

    def test_multiple_funcs(self):
        func = snug._compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func('30', base=5) == '16'


def test_empty_mapping():
    empty = snug._EMPTY_MAPPING
    assert isinstance(empty, collections.Mapping)
    assert empty == {}
    with pytest.raises(KeyError):
        empty['foo']

    assert len(empty) == 0
    assert list(empty) == []
    assert repr(empty) == '{<empty>}'
    assert not empty
