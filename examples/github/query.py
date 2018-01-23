import json
import reprlib
import typing as t
from datetime import datetime
from functools import partial
from operator import attrgetter

from dataclasses import dataclass

import snug
from gentools import map_yield, map_send, map_return, oneyield, reusable
from toolz import valfilter, compose

from .load import registry
from . import types

API_PREFIX = 'https://api.github.com/'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}

_repr = reprlib.Repr()
_repr.maxstring = 45
dclass = partial(dataclass, frozen=True)
basic_interaction = compose(
    map_yield(snug.prefix_adder(API_PREFIX), snug.header_adder(HEADERS)),
    map_send(compose(json.loads, attrgetter('data'))),
    oneyield,
)
loads = compose(map_return, registry)


def inspect(x):
    import pdb; pdb.set_trace()
    return x


def notnone(x):
    return x is not None


@dclass
class repo(snug.Query):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    @loads(types.Repo)
    @basic_interaction
    def __iter__(self):
        return snug.GET(f'repos/{self.owner}/{self.name}')

    @reusable
    @loads(t.List[types.Issue])
    @basic_interaction
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
    @loads(types.Issue)
    @basic_interaction
    def issue(repo: 'repo', number: int):
        """get a specific issue in the repo"""
        return snug.GET(
            f'repos/{repo.owner}/'
            f'{repo.name}/issues/{number}')


@reusable
@loads(t.List[types.RepoSummary])
@basic_interaction
def repos():
    """recent repositories"""
    return snug.GET('repositories')


@reusable
@loads(types.Organization)
@basic_interaction
def org(login: str):
    """Organization lookup by login"""
    return snug.GET(f'orgs/{login}')


@reusable
@loads(t.List[types.OrganizationSummary])
@basic_interaction
def orgs():
    """a selection of organizations"""
    return snug.GET('organizations')


@reusable
@loads(t.List[types.Issue])
@basic_interaction
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


@dclass
class current_user(snug.Query):
    """a reference to the current user"""

    @loads(types.User)
    @basic_interaction
    def __iter__(self):
        return snug.GET('user')

    @staticmethod
    @reusable
    @loads(t.List[types.Issue])
    @basic_interaction
    def issues():
        return snug.GET('user/issues')


CURRENT_USER = current_user()
