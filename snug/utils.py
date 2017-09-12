"""Miscellaneous tools and boilerplate"""
import abc

from functools import partial as _partial


def identity(obj):
    """identity function: returns the input unmodified"""
    return obj


class compose:
    """a function composed of various functions"""

    def __init__(self, *funcs):
        self.funcs = funcs

    def __call__(self, *args, **kwargs):
        iterfuncs = reversed(self.funcs)
        first = next(iterfuncs, identity)
        value = first(*args, **kwargs)
        for func in iterfuncs:
            value = func(value)
        return value

    def __eq__(self, other):
        return isinstance(other, compose) and self.funcs == other.funcs


class partial(_partial):
    '''like functools.partial, but allows positional arguments
    by use of ellipsis (...).
    Useful for builtin python functions which do not take keyword args

        >>> countdown = partial(range, ..., 0, -1)
        >>> list(countdown(3))
        [3, 2, 1]
    '''
    def __call__(self, *args, **keywords):
        iter_args = iter(args)
        merged_args = (next(iter_args) if a is ... else a
                       for a in self.args)
        merged_keywords = {**self.keywords, **keywords}
        return self.func(*merged_args, *iter_args, **merged_keywords)


class SlotsMeta(abc.ABCMeta):

    def __new__(self, name, bases, ns):

        fields = ns.pop('__annotations__', {})

        defaults = {}
        for field in fields:
            try:
                defaults[field] = ns.pop(field)
            except KeyError:
                pass

        ns.update({
            '__slots__': fields,
            'DEFAULTS': defaults,
        })
        return super().__new__(self, name, bases, ns)


class Slots(metaclass=SlotsMeta):
    """base class for simple data containers.
    Basically namedtuple without tuple."""

    def __init__(self, *args, **kwargs):
        fields = self.__slots__
        pos_args = dict(zip(fields, args))
        duplicates = pos_args.keys() & kwargs.keys()
        if duplicates:
            raise TypeError(f'duplicate argument(s): {tuple(duplicates)}')

        all_args = {**self.DEFAULTS, **pos_args, **kwargs}
        missing = set(fields) - all_args.keys()
        if missing:
            raise TypeError(f'missing argument(s): {tuple(missing)}')

        for name, value in all_args.items():
            setattr(self, name, value)

    def __eq__(self, other):
        fields = self.__slots__
        return (
            isinstance(other, self.__class__)
            and all(
                v1 == v2
                for v1, v2 in zip(
                    map(self.__getattribute__, fields),
                    map(other.__getattribute__, fields)
                )
            )
        )

    def __repr__(self):
        fields_repr = ', '.join([
            f'{name}={getattr(self, name)!r}'
            for name in self.__slots__
        ])
        return f'{self.__class__.__name__}({fields_repr})'

    def _astuple(self):
        """return a tuple with the fields"""
        return tuple(map(self.__getattribute__, self.__slots__))

    def _asdict(self):
        """return a dict with the field values"""
        fields = self.__slots__
        values = map(self.__getattribute__, fields)
        return dict(zip(fields, values))

    def _replace(self, **kwargs):
        newfields = {**self._asdict(), **kwargs}
        return self.__class__(**newfields)
