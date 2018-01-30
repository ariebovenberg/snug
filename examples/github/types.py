"""datastructures and type definitions"""
import enum
import reprlib
import typing as t
from datetime import datetime
from functools import partial

from dataclasses import dataclass

_repr = reprlib.Repr()
_repr.maxstring = 45


dclass = partial(dataclass, frozen=True, repr=False)


@dclass()
class UserSummary:
    login:       str
    id:          int
    avatar_url:  str
    gravatar_id: str
    # full:        'User'
    html_url:    str
    type:        str
    site_admin:  bool

    def __repr__(self):
        return f'<User: {self.login}>'


@dclass()
class User(UserSummary):
    bio:        str
    blog:       str
    company:    str
    created_at: datetime
    email:      str
    id:         str
    location:   str
    login:      str
    name:       str
    repos_url:  str
    site_admin: str
    updated_at: datetime
    url:        str


@dclass()
class RepoSummary:
    id:          int
    owner:       UserSummary
    name:        str
    full_name:   str
    description: str
    private:     bool
    fork:        bool
    url:         str
    html_url:    str

    def __repr__(self):
        return f'<RepoSummary: {self.name} | {_repr.repr(self.description)}>'


@dclass()
class Repo(RepoSummary):
    created_at:        datetime
    default_branch:    str
    description:       str
    full_name:         str
    homepage:          str
    id:                int
    language:          str
    name:              str
    open_issues_count: int
    owner:             UserSummary
    private:           bool
    pushed_at:         datetime
    size:              float
    stargazers_count:  int
    updated_at:        datetime
    watchers_count:    int


@dclass()
class OrganizationSummary:
    """basic details of a github organization"""
    id:          int
    description: t.Optional[str]
    login:       str


@dclass()
class Organization(OrganizationSummary):
    """a github organization"""
    blog:        t.Optional[str]
    created_at:  t.Optional[datetime]
    name:        t.Optional[str]
    repos_url:   str
    type:        t.Optional[str]

    def __repr__(self):
        return '<Organization: {self.login}>'


@dclass()
class Issue:
    """a github issue or pull-request"""

    class State(enum.Enum):
        OPEN = 'open'
        CLOSED = 'closed'
        ALL = 'all'

    number: str
    title: str
    body: str
    state: State

    def __repr__(self):
        return f'<Issue: #{self.number} {self.title}>'

    class Sort(enum.Enum):
        CREATED = 'created'
        UPDATED = 'updated'
        COMMENTS = 'comments'

    class Filter(enum.Enum):
        ASSIGNED = 'assigned'
        CREATED = 'created'
        MENTIONED = 'mentioned'
        SUBSCRIBED = 'subscribed'
        ALL = 'all'

    @dclass
    class Comment:
        """an issue comment"""
        id:   int
        user: UserSummary
        body: str
