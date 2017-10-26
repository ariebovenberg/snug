import json
import reprlib
import typing as t
from datetime import datetime
from operator import methodcaller, attrgetter

import snug
from toolz import flip, partial, valfilter, compose
from dataclasses import dataclass
from snug.utils import notnone

from .types import Repo, Organization, User, Issue, RepoSummary
from .load import load

parse_datetime = partial(flip(datetime.strptime), '%Y-%m-%dT%H:%M:%SZ')

_repr = reprlib.Repr()
_repr.maxstring = 45


api = snug.Api(
    prepare=compose(
        methodcaller('add_headers',
                     {'Accept': 'application/vnd.github.v3+json'}),
        methodcaller('add_prefix', 'https://api.github.com/')),
    parse=compose(
        json.loads,
        methodcaller('decode', 'utf-8'),
        attrgetter('content')))


resolve = partial(snug.query.resolve, api=api, load=load)


@dataclass(frozen=True)
class repo(snug.Query, rtype=Repo):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    @property
    def __req__(self):
        return snug.Request(f'repos/{self.owner}/{self.name}')

    @snug.query.from_func(rtype=t.List[Issue])
    def issues(repo:   'repo',
               labels: t.Optional[str]=None,
               state:  t.Optional[str]=None):
        return snug.Request(
            f'repos/{repo.owner}/{repo.name}/issues',
            params=valfilter(notnone, {
                'labels': labels,
                'state':  state,
            }))

    @snug.query.from_func(rtype=Issue)
    def issue(repo: 'repo', number: int):
        return snug.Request(
            f'repos/{repo.owner}/'
            f'{repo.name}/issues/{number}')


@snug.query.from_func(rtype=t.List[RepoSummary])
def repos():
    """a selection on repositories"""
    return snug.Request('repositories')


@snug.query.from_func(rtype=Organization)
def org(login: str):
    """Organization lookup by login"""
    return snug.Request(f'orgs/{login}')


@snug.query.from_func(rtype=t.List[Organization])
def orgs():
    """a selection of organizations"""
    return snug.Request('organizations')


@snug.query.from_func(rtype=t.List[Issue])
def issues(filter: t.Optional[str]=None,
           state:  t.Optional[Issue.State]=None,
           labels: t.Optional[str]=None,
           sort:   t.Optional[Issue.Sort]=None,
           since:  t.Optional[datetime]=None):
    """a selection of assigned issues"""
    return snug.Request('issues', params=valfilter(notnone, {
        'filter': filter,
        'state':  state,
        'labels': labels,
        'sort':   sort,
        'since':  since,
    }))


@dataclass(frozen=True)
class current_user(snug.Query, rtype=User):
    """a reference to the current user"""

    @property
    def __req__(self):
        return snug.Request('user')

    @snug.query.from_func(rtype=t.List[Issue])
    def issues(user: 'current_user'):
        return snug.Request('user/issues')
