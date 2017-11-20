import typing as t
from datetime import datetime
from operator import itemgetter

import snug
from toolz import flip, partial

from . import types

registry = snug.load.PrimitiveRegistry({
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
}) | snug.load.GenericRegistry({
    t.List: snug.load.list_loader
}) | snug.load.get_optional_loader | snug.load.AutoDataclassRegistry()
