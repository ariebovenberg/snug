import json
import reprlib
import typing as t
from datetime import datetime
from operator import attrgetter

from dataclasses import dataclass
from gentools import map_return, map_send, map_yield, oneyield, reusable
from toolz import compose, valfilter

import snug

from . import types
from .load import registry

API_PREFIX = 'https://api.github.com/'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}

_repr = reprlib.Repr()
_repr.maxstring = 45
basic_interaction = compose(
    map_yield(snug.prefix_adder(API_PREFIX), snug.header_adder(HEADERS)),
    map_send(compose(json.loads, attrgetter('data'))),
    oneyield,
)


def retrieves(rtype):
    """decorator factory for simple retrieval queries"""
    return compose(map_return(registry(rtype)), basic_interaction)


def notnone(x):
    return x is not None


@dataclass
class repo(snug.Query):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    @retrieves(types.Repo)
    def __iter__(self):
        return snug.GET(f'repos/{self.owner}/{self.name}')

    @reusable
    @retrieves(t.List[types.Issue])
    def issues(repo: 'repo',
               labels: t.Optional[str]=None,
               state:  t.Optional[str]=None):
        """get the issues for this repo"""
        return snug.GET(
            f'repos/{repo.owner}/{repo.name}/issues',
            params=valfilter(notnone, {
                'labels': labels,
                'state':  state,
            }))

    @reusable
    @retrieves(types.Issue)
    def issue(repo: 'repo', number: int):
        """get a specific issue in the repo"""
        return snug.GET(
            f'repos/{repo.owner}/'
            f'{repo.name}/issues/{number}')


@reusable
@retrieves(t.List[types.RepoSummary])
def repos():
    """recent repositories"""
    return snug.GET('repositories')


@reusable
@retrieves(types.Organization)
def org(login: str):
    """Organization lookup by login"""
    return snug.GET(f'orgs/{login}')


@reusable
@retrieves(t.List[types.OrganizationSummary])
def orgs():
    """a selection of organizations"""
    return snug.GET('organizations')


@reusable
@retrieves(t.List[types.Issue])
def issues(filter: t.Optional[str]=None,
           state:  t.Optional[types.Issue.State]=None,
           labels: t.Optional[str]=None,
           sort:   t.Optional[types.Issue.Sort]=None,
           since:  t.Optional[datetime]=None):
    """a selection of assigned issues"""
    return snug.GET('issues', params=valfilter(notnone, {
        'filter': filter,
        'state':  state,
        'labels': labels,
        'sort':   sort,
        'since':  since,
    }))


@dataclass
class current_user(snug.Query):
    """a reference to the current user"""

    @retrieves(types.User)
    def __iter__(self):
        return snug.GET('user')

    @staticmethod
    @reusable
    @retrieves(t.List[types.Issue])
    def issues():
        return snug.GET('user/issues')


CURRENT_USER = current_user()
