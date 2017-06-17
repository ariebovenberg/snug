import functools


class ppartial(functools.partial):
    """functools.partial with support for positional args"""

    def __call__(self, *args, **keywords):
        iter_args = iter(args)
        merged_args = (next(iter_args) if a is ... else a
                       for a in self.args)
        merged_keywords = {**self.keywords, **keywords}
        return self.func(*merged_args, **merged_keywords)
