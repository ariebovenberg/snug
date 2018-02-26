import collections

import pytest

import snug


def test_identity():
    obj = object()
    assert snug._identity(obj) is obj


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
