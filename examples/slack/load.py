"""deserialization tools"""
import typing as t
from datetime import datetime

from valuable import load
from . import types
from toolz import compose


def page_loader(subloaders, value):
    loader, = subloaders
    objects_key, = (k for k in value
                    if k != 'response_metadata' and k != 'ok')
    try:
        next_cursor = value['response_metadata']['next_cursor']
    except KeyError:
        next_cursor = None
    return types.Page(
        list(map(loader, value[objects_key])),
        next_cursor=next_cursor
    )


registry = load.MultiRegistry(
    load.PrimitiveRegistry({
        datetime: compose(datetime.utcfromtimestamp, float),
        int:      int,
        float:    float,
        bool:     bool,
        str:      str,
    }),
    load.GenericRegistry({
        t.List: load.list_loader,
        types.Page: page_loader,
    }),
    load.AutoDataclassRegistry(),
)
