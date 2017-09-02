"""Miscellaneous tools and boilerplate"""
from functools import reduce, partial as _partial


def identity(obj):
    """identity function: returns the input unmodified"""
    return obj


def compose(*functions):
    """compose a function from a list of functions"""
    return reduce(lambda f, g: lambda x: f(g(x)), functions, identity)


class partial(_partial):
    '''like functools.partial, but allows positional arguments
    by use of ellipsis (...).
    Useful for builtin python functions which do not take keyword args

        >>> count_down_from = partial(range, ..., 0, -1)
        >>> list(count_down_from(3))
        [3, 2, 1]
    '''
    def __call__(self, *args, **keywords):
        iter_args = iter(args)
        merged_args = (next(iter_args) if a is ... else a
                       for a in self.args)
        merged_keywords = {**self.keywords, **keywords}
        return self.func(*merged_args, *iter_args, **merged_keywords)
