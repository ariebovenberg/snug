import functools

from omgorm import utils


def _example_func(*args, **kwargs):
    return args, kwargs


class TestPPartial:

    def test_is_subclass(self):
        assert issubclass(utils.ppartial, functools.partial)

    def test_positional_args(self):
        func = utils.ppartial(_example_func, ..., ..., 'foo', ...,
                              bla='bing', another='thing')

        args, kwargs = func(1, 2, 3, another='thing2')

        assert args == (1, 2, 'foo', 3)
        assert kwargs == {'bla': 'bing', 'another': 'thing2'}
