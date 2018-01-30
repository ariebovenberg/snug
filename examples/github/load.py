"""deserialization tools"""
import typing as t
from datetime import datetime
from functools import partial

from toolz import flip
from valuable import load

from . import types

registry = load.PrimitiveRegistry({
    datetime: partial(flip(datetime.strptime),  '%Y-%m-%dT%H:%M:%SZ'),
    **{
        c: c for c in [
            int,
            float,
            bool,
            str,
            types.Issue.State
        ]
    }
}) | load.GenericRegistry({
    t.List: load.list_loader
}) | load.get_optional_loader | load.AutoDataclassRegistry()
