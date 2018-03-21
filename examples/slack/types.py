import typing as t
from datetime import datetime
from dataclasses import dataclass
from operator import attrgetter

import snug

T = t.TypeVar('T')


@dataclass(repr=False)
class UpdatedString:
    """a string with extra info on when it was last set"""
    value:    str
    creator:  str
    last_set: datetime

    def __repr__(self):
        return f'"{self.value}" (updated {self.last_set:%x})'


@dataclass(repr=False)
class Channel:
    """summary of a channel"""
    id:              str
    name:            str
    is_channel:      bool
    created:         datetime
    creator:         str
    is_archived:     bool
    is_general:      bool
    name_normalized: str
    is_shared:       bool
    is_org_shared:   bool
    is_member:       bool
    is_private:      bool
    is_mpim:         bool
    members:         t.List[str]
    topic:           UpdatedString
    purpose:         UpdatedString
    previous_names:  t.List[str]

    def __repr__(self):
        return (f'<{self.__class__.__name__}: #{self.name}'
                f'{" (archived)" if self.is_archived else ""}>')


@dataclass(repr=False)
class Message:
    text:     str
    username: str
    type:     str
    ts:       datetime


@dataclass
class Page(t.Generic[T]):
    """a page of objects"""
    content:    t.List[T]
    next_query: snug.Query['Page']

    def __iter__(self):
        yield from self.content

    def __getitem__(self, index):
        return self.content[index]

    def __len__(self):
        return len(self.content)
