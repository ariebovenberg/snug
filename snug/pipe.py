"""middleware abstractions"""
import typing as t

from .core import T_req, T_resp


def identity(request: T_req) -> t.Generator[T_req, T_resp, T_resp]:
    """identity pipe, leaves requests and responses unchanged"""
    return (yield request)
