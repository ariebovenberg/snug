import collections
import inspect
from operator import attrgetter

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

    def test_called_as_method(self):

        class Foo:
            def __init__(self, value):
                self.value = value
            func = utils.compose(lambda x: x + 1, attrgetter('value'))

        f = Foo(4)
        assert Foo.func(f) == 5
        assert f.func() == 5

    def test_equality(self):
        func = utils.compose(int, str)
        other = utils.compose(int, str)
        assert func == other
        assert not func != other
        assert hash(func) == hash(other)

        assert not func == utils.compose(int)
        assert func != utils.compose(int)

        assert func != object()
        assert not func == object()

    def test_signature(self):

        def func1(x: str, foo, *args, c=4) -> int:
            return int(x) + foo + c

        def func2(f: int) -> str:
            return 'a' * f

        func = utils.compose(
            func2,
            lambda x: x + 4,
            func1)

        sig = inspect.signature(func)
        assert sig.parameters == inspect.signature(func1).parameters
        assert sig.return_annotation == inspect.signature(
            func2).return_annotation


def test_called_as_method():

    class Parent:
        @utils.called_as_method
        class Child:
            def __init__(self, parent, foo):
                self.parent, self.foo = parent, foo

    parent = Parent()

    child = parent.Child(4)
    assert child.parent is parent
    assert child.foo == 4

    child = Parent.Child(parent, 4)
    assert child.parent is parent
    assert child.foo == 4


def test_empty_mapping():
    assert isinstance(utils.EMPTY_MAPPING, collections.Mapping)
    assert utils.EMPTY_MAPPING == {}
    with pytest.raises(KeyError):
        utils.EMPTY_MAPPING['foo']

    assert len(utils.EMPTY_MAPPING) == 0
    assert list(utils.EMPTY_MAPPING) == []
    assert repr(utils.EMPTY_MAPPING) == '{}'
    assert not utils.EMPTY_MAPPING
