"""Tools for creating queries and query classes"""
import abc
import typing as t
from dataclasses import make_dataclass
from functools import partial, partialmethod

from .core import Pipe, Query, T, T_req, T_resp, nest
from .utils import apply, as_tuple, compose, dclass, func_to_fields, identity

__all__ = [
    'Fixed',
    'Base',
    'Piped',
    'cls_from_gen',
    'cls_from_func',
    'called_as_method',
    'piped',
]


@dclass
class Fixed(Query[T, T_req, T_resp]):
    """A static query. Useful for queries which do not take parameters.

    Parameters
    ----------
    request
        the request object
    load
        response loader

    Examples
    --------

    >>> latest_posts = query.Fixed('/posts/latest')
    >>> current_user = query.Fixed('/user/', load=load_user)
    """
    request: T_req
    load:    t.Callable[[T_resp], T] = identity

    def __resolve__(self):
        return self.load((yield self.request))


class Base(Query[T, T_req, T_resp]):
    """Base class for query subclasses with useful methods to override

    Example
    -------

    >>> class post(query.Base):
    ...     def __init__(self, id):
    ...         self.id = id
    ...
    ...     def _request(self):
    ...         return f'/posts/{self.id}/'
    """

    @abc.abstractmethod
    def _request(self) -> T_req:
        """override this method to implement a request creator"""
        raise NotImplementedError

    def _parse(self, response: T_resp) -> T:
        """override this method to provide custom loading of responses

        Parameters
        ----------
        response
            the response to parse
        """
        return response

    def __resolve__(self):
        return self._parse((yield self._request()))


@dclass
class Piped(Query[T, T_req, T_resp]):
    """A query with a pipe modifying requests/responses

    Parameters
    ----------
    pipe
        the pipe to apply
    inner
        the inner query

    Example
    -------

    >>> query.Piped(jsondata, inner=query.Fixed('/posts/latest/'))

    """
    pipe:  Pipe
    inner: Query

    def __resolve__(self):
        resolver = self.inner.__resolve__()
        return nest(resolver, self.pipe)


@dclass
class piped:
    """decorator which wraps a class' ``__resolve__`` method through a Pipe

    Note
    ----
    the class is modified in place
    """
    thru: Pipe

    def __call__(self, cls):
        assert isinstance(cls, type)
        cls.__resolve__ = called_as_method(
            WrappedGenfunc(pipe=self.thru, gen=cls.__resolve__))
        return cls


@dclass
class WrappedGenfunc:
    pipe: Pipe
    gen:  t.Generator

    def __call__(self, *args, **kwargs):
        return nest(self.gen(*args, **kwargs), self.pipe)


@dclass
class called_as_method:
    """decorate a callable (e.g. class or function) to be called as a method.
    I.e. the parent instance is passed as the first argument"""
    target: t.Callable

    def __get__(self, instance, cls):
        return (self.target if instance is None
                else partial(self.target, instance))


class cls_from_gen:
    """Create a query class from a generator function

    Example
    -------

    >>> @query.cls_from_gen()
    ... def post(id: int):
    ...     return json.loads((yield f'posts/{id}/'))

    Note
    ----
    The function must:

    * be a python function, bound to a module.
    * be fully annotated, without keyword-only arguments
    """
    def __call__(self,
                 func: t.Callable[..., t.Generator[T_req, T_resp, T]]) -> (
                     t.Type[Query[T, T_req, T_resp]]):
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Query, ),
            namespace={
                '__doc__':     func.__doc__,
                '__module__':  func.__module__,
                '__resolve__': partialmethod(compose(
                    partial(apply, func), as_tuple)),
            }
        )


class cls_from_func:
    """Create a query class from a function. Use as a decorator.

    Parameters
    ----------
    load
        function to parse the response

    Example
    -------

    >>> @query.cls_from_func(load=load_post)
    ... def post(id: int):
    ...     return f'posts/{id}/'

    Note
    ----
    The function must:

    * be a python function, bound to a module.
    * be fully annotated, without keyword-only arguments
    """
    # keyword-only arguments to prevent incorrect decorator usage
    def __init__(self, *, load: t.Callable[[T_resp], T]=identity):
        self.load = load

    def __call__(self, func: t.Callable[..., T_req]) -> t.Type[
            Query[T, T_req, T_resp]]:
        return make_dataclass(
            func.__name__,
            func_to_fields(func),
            bases=(Base, ),
            namespace={
                '__doc__':    func.__doc__,
                '__module__': func.__module__,
                '_request':   partialmethod(compose(
                    partial(apply, func), as_tuple)),
                '_parse':     staticmethod(self.load)
            })
