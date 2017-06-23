"""Miscellaneous tools and boilerplate"""
import itertools
import functools
import sys


class ppartial(functools.partial):
    '''like functools.partial, but allows positional arguments
    by use of ellipsis (...).
    Useful for builtin python functions which do not take keyword args

        >>> count_down_from = ppartial(range, ..., 0, -1)
        >>> list(count_down_from(3))
        [3, 2, 1]
    '''
    def __call__(self, *args, **keywords):
        iter_args = iter(args)
        merged_args = (next(iter_args) if a is ... else a
                       for a in self.args)
        # keywords may be ``None`` in some python 3.4.x versions
        merged_keywords = {} if self.keywords is None else self.keywords.copy()
        merged_keywords.update(keywords)
        return self.func(*itertools.chain(merged_args, iter_args),
                         **merged_keywords)


class EnsurePep487Meta(type):  # pragma: no cover
    """metaclass to ensure rudimentary support for PEP487 in Py<=3.6"""
    if sys.version_info < (3, 6):

        def __new__(cls, name, bases, classdict, **kwargs):
            return super().__new__(cls, name, bases, classdict)

        def __init__(cls, name, bases, dct, **kwargs):
            if bases and hasattr(cls, '__init_subclass__'):
                cls.__init_subclass__(cls, **kwargs)

            for name, item in dct.items():
                if hasattr(item, '__set_name__'):
                    item.__set_name__(cls, name)
