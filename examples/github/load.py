import typing as t
from datetime import datetime

import snug
from toolz import flip, partial

from . import types

_loaders = {
    datetime: partial(flip(datetime.strptime),  '%Y-%m-%dT%H:%M:%SZ')
}
_loaders.update(
    (c, c) for c in [
        int,
        float,
        bool,
        str,
        types.Issue.State
    ]
)
_loaders[t.List] = snug.load.list_
_loaders[t.Optional] = snug.load.optional

load = snug.load.load(loaders=_loaders)


def register_dataclass_loader(cls, overrides=(), skip=()):
    fields = {name: name for name in cls.__dataclass_fields__
              if name not in skip}
    fields.update(overrides)
    return snug.load.registered_dataclass_loader(cls, fields, loaders=_loaders)


register_dataclass_loader(types.Repo)
register_dataclass_loader(types.Issue)
register_dataclass_loader(types.Organization)
register_dataclass_loader(types.User)
register_dataclass_loader(types.RepoSummary)
register_dataclass_loader(types.UserSummary)
