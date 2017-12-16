import json
import reprlib
import typing as t
from dataclasses import dataclass
from datetime import datetime
from functools import partial

import snug
from snug.utils import notnone, valfilter

from .load import registry as loads
from .types import Issue, Organization, Repo, RepoSummary, User

_repr = reprlib.Repr()
_repr.maxstring = 45


dclass = partial(dataclass, frozen=True)


@snug.wrap.Fixed
def github_middleware(request):
    response = yield request.add_headers({
        'Accept': 'application/vnd.github.v3+json',
    }).add_prefix('https://api.github.com/')
    return json.loads(response.data.decode('utf-8'))


resolver = partial(snug.build_resolver,
                   wrapper=github_middleware,
                   sender=snug.urllib_sender(),
                   authenticator=snug.Request.add_basic_auth)


async_resolver = partial(snug.build_async_resolver,
                         wrapper=github_middleware,
                         authenticator=snug.Request.add_basic_auth)


@dclass
class repo(snug.query.Base):
    """repository lookup by owner & name"""
    owner: str
    name:  str

    def _request(self):
        return snug.Request(f'repos/{self.owner}/{self.name}')

    _parse = staticmethod(loads(Repo))

    @snug.query.from_requester(load=loads(t.List[Issue]), nestable=True)
    def issues(repo:   'repo',
               labels: t.Optional[str]=None,
               state:  t.Optional[str]=None):
        return snug.Request(
            f'repos/{repo.owner}/{repo.name}/issues',
            params=valfilter(notnone, {
                'labels': labels,
                'state':  state,
            }))

    @snug.query.from_requester(load=loads(Issue), nestable=True)
    def issue(repo: 'repo', number: int):
        return snug.Request(
            f'repos/{repo.owner}/'
            f'{repo.name}/issues/{number}')


@snug.query.from_requester(load=loads(t.List[RepoSummary]))
def repos():
    """a selection on repositories"""
    return snug.Request('repositories')


@snug.query.from_requester(load=loads(Organization))
def org(login: str):
    """Organization lookup by login"""
    return snug.Request(f'orgs/{login}')


@snug.query.from_requester(load=loads(t.List[Organization]))
def orgs():
    """a selection of organizations"""
    return snug.Request('organizations')


@snug.query.from_requester(load=loads(t.List[Issue]))
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
class current_user(snug.query.Base):
    """a reference to the current user"""

    def _request(self):
        return snug.Request('user')

    _parse = staticmethod(loads(User))

    @snug.query.from_requester(load=loads(t.List[Issue]))
    def issues():
        return snug.Request('user/issues')
