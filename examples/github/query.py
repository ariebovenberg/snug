import json
import reprlib
import typing as t
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from operator import attrgetter

import snug
from snug.utils import notnone, valfilter, compose, oneyield

from .load import registry as loads
from .types import Issue, Organization, Repo, RepoSummary, User

_repr = reprlib.Repr()
_repr.maxstring = 45

dclass = partial(dataclass, frozen=True)

API_PREFIX = 'https://api.github.com/'
add_prefix = snug.http.prefix_adder(API_PREFIX)
add_headers = snug.http.header_adder({
    'Accept': 'application/vnd.github.v3+json',
})
parse_response = compose(json.loads, attrgetter('data'))

basic_interaction = compose(
    snug.yieldmapped(add_prefix, add_headers),
    snug.sendmapped(parse_response),
)

exec = snug.http.simple_exec()
authed_exec = snug.http.authed_exec
authed_aexec = snug.http.authed_aexec


@dclass
class repo(snug.Query):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    @snug.returnmapped(loads(Repo))
    @basic_interaction
    @oneyield
    def __iter__(self):
        return snug.http.GET(f'repos/{self.owner}/{self.name}')

    @snug.querytype(related=True)
    @snug.returnmapped(loads(t.List[Issue]))
    @basic_interaction
    @oneyield
    def issues(repo:   'repo',
               labels: t.Optional[str]=None,
               state:  t.Optional[str]=None):
        return snug.http.GET(
            f'repos/{repo.owner}/{repo.name}/issues',
            params=valfilter(notnone, {
                'labels': labels,
                'state':  state,
            }))

    @snug.querytype(related=True)
    @snug.returnmapped(loads(Issue))
    @basic_interaction
    @oneyield
    def issue(repo: 'repo', number: int):
        return snug.http.GET(
            f'repos/{repo.owner}/'
            f'{repo.name}/issues/{number}')


@snug.querytype()
@snug.returnmapped(loads(t.List[RepoSummary]))
@basic_interaction
@oneyield
def repos():
    """a selection on repositories"""
    return snug.http.GET('repositories')


@snug.querytype()
@snug.returnmapped(loads(Organization))
@basic_interaction
@oneyield
def org(login: str):
    """Organization lookup by login"""
    return snug.http.GET(f'orgs/{login}')


@snug.querytype()
@snug.returnmapped(loads(t.List[Organization]))
@basic_interaction
@oneyield
def orgs():
    """a selection of organizations"""
    return snug.http.GET('organizations')


@snug.querytype()
@snug.returnmapped(loads(t.List[Issue]))
@basic_interaction
@oneyield
def issues(filter: t.Optional[str]=None,
           state:  t.Optional[Issue.State]=None,
           labels: t.Optional[str]=None,
           sort:   t.Optional[Issue.Sort]=None,
           since:  t.Optional[datetime]=None):
    """a selection of assigned issues"""
    return snug.http.GET('issues', params=valfilter(notnone, {
        'filter': filter,
        'state':  state,
        'labels': labels,
        'sort':   sort,
        'since':  since,
    }))


@dataclass(frozen=True)
class current_user(snug.Query):
    """a reference to the current user"""

    @snug.returnmapped(loads(User))
    @basic_interaction
    @oneyield
    def __iter__(self):
        return snug.http.GET('user')

    @snug.querytype()
    @snug.returnmapped(loads(t.List[Issue]))
    @basic_interaction
    @oneyield
    def issues():
        return snug.http.GET('user/issues')
