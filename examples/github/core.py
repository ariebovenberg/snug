import operator
import reprlib
import typing as t
from datetime import datetime
from operator import truth

import snug
from toolz import flip, partial, valfilter
from dataclasses import dataclass, asdict

from . import types

parse_datetime = partial(flip(datetime.strptime), '%Y-%m-%dT%H:%M:%SZ')

_repr = reprlib.Repr()
_repr.maxstring = 45


api = snug.Api('https://api.github.com/',
               headers={'Accept': 'application/vnd.github.v3+json'},
               parse_response=operator.methodcaller('json'))


@dataclass(frozen=True)
class repo(snug.Item, type=types.Repo):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    def __request__(self):
        return snug.Request(f'repos/{self.owner}/{self.name}')

    @dataclass(frozen=True)
    class issues(snug.QuerySet, type=types.Issue):
        """a set of issues for a repository"""
        repo: 'repo'
        labels: str = None
        state: str = None

        def __request__(self):
            params = asdict(self)
            params.pop('repo')
            return snug.Request(
                f'repos/{self.repo.owner}/{self.repo.name}/issues',
                params=valfilter(truth, params))

    @dataclass(frozen=True)
    class issue(snug.Item, type=types.Issue):
        repo: 'repo'
        number: int

        def __request__(self):
            return snug.Request(
                f'repos/{self.repo.owner}/'
                f'{self.repo.name}/issues/{self.number}')


@dataclass(frozen=True)
class repos(snug.QuerySet, type=types.Repo):
    """a selection on repositories"""

    def __request__(self):
        return snug.Request('repositories')


@dataclass(frozen=True)
class org(snug.Item, type=types.Organization):
    """Organization lookup by login"""
    login: str

    def __request__(self):
        return snug.Request(f'orgs/{self.login}')


@dataclass(frozen=True)
class orgs(snug.QuerySet, type=types.Organization):

    def __request__(self):
        return snug.Request('organizations')


@dataclass(frozen=True)
class issue(snug.Item, type=types.Issue):
    """an issue referenced by repo & number"""
    repo: t.Union['Repo', 'repo']
    number: int

    def __request__(self):
        return snug.Request(f'repos/{self.repo.owner}/{self.repo.name}/'
                            f'issues/{self.number}')


@dataclass(frozen=True)
class issues(snug.QuerySet, type=types.Issue):
    """a selection of assigned issues"""
    filter: t.Optional[str] = None
    state:  t.Optional['Issue.State'] = None
    labels: t.Optional[str] = None
    sort:   t.Optional['Issue.Sort'] = None
    since:  t.Optional[datetime] = None

    def __request__(self):
        params = valfilter(truth, asdict(self))
        return snug.Request('issues', params=params)


@dataclass(frozen=True)
class current_user(snug.Item, type=types.User):
    """a reference to the current user"""

    def __request__(self):
        return snug.Request('user')

    @dataclass(frozen=True)
    class issues(snug.QuerySet, type=types.Issue):
        user: 'User'

        def __request__(self):
            return snug.Request('user/issues')
