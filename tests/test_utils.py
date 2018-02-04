import collections
import inspect

import pytest

from snug import utils


def test_identity():
    obj = object()
    assert utils.identity(obj) is obj


class TestCompose:

    def test_empty(self):
        obj = object()
        func = utils.compose()
        assert func(obj) is obj
        assert isinstance(func.funcs, tuple)
        assert func.funcs == ()
        assert inspect.signature(func) == inspect.signature(utils.identity)

    def test_one_func_with_multiple_args(self):
        func = utils.compose(int)
        assert func('10', base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int, )

    def test_multiple_funcs(self):
        func = utils.compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func('30', base=5) == '16'


def test_empty_mapping():
    assert isinstance(utils.EMPTY_MAPPING, collections.Mapping)
    assert utils.EMPTY_MAPPING == {}
    with pytest.raises(KeyError):
        utils.EMPTY_MAPPING['foo']

    assert len(utils.EMPTY_MAPPING) == 0
    assert list(utils.EMPTY_MAPPING) == []
    assert repr(utils.EMPTY_MAPPING) == '{<empty>}'
    assert not utils.EMPTY_MAPPING
