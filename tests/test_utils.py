import operator
import functools

from snug import utils


def _example_func(*args, **kwargs):
    return args, kwargs


class TestPartial:

    def test_is_subclass(self):
        assert issubclass(utils.partial, functools.partial)

    def test_placeholder(self):
        func = utils.partial(_example_func, ..., ..., 'foo', ...,
                             bla='bing', another='thing')

        args, kwargs = func(1, 2, 3, another='thing2')

        assert args == (1, 2, 'foo', 3)
        assert kwargs == {'bla': 'bing', 'another': 'thing2'}

    def test_no_placeholders(self):
        func = utils.partial(_example_func, 'foo', 5)
        args, kwargs = func(10)

        assert args == ('foo', 5, 10)
        assert not kwargs


class TestCompose:

    def test_empty(self):
        func = utils.compose()
        assert func('abc') == 'abc'

    def test_multiple(self):
        func = utils.compose(
            str,
            utils.partial(operator.add, 5),
            utils.partial(operator.truediv, 1)
        )
        assert func(4) == '5.25'
