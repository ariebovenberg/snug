"""the main API"""
import json
import reprlib
import typing as t
from datetime import datetime
from functools import singledispatch
from operator import attrgetter, methodcaller

from dataclasses import dataclass
from gentools import (compose, map_return, map_send, map_yield, oneyield,
                      reusable)

import snug

from . import types
from .load import registry

API_PREFIX = 'https://api.github.com/'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}

_repr = reprlib.Repr()
_repr.maxstring = 45


class ApiError(Exception):
    pass


@singledispatch
def dump_param(val):
    """dump a query param value"""
    return str(val)


dump_param.register(datetime, methodcaller('strftime', '%Y-%m-%dT%H:%M:%SZ'))


def prepare_params(request):
    """prepare request parameters"""
    return request.replace(
        params={key: dump_param(val) for key, val in request.params.items()
                if val is not None})


def check_errors(response):
    if response.status_code == 400:
        try:
            msg = json.loads(response.content)['message']
        except (KeyError, ValueError):
            msg = ''
        raise ApiError(msg)
    return response


basic_interaction = compose(
    map_yield(prepare_params,
              snug.prefix_adder(API_PREFIX),
              snug.header_adder(HEADERS)),
    map_send(check_errors),
)


def retrieves(rtype):
    """decorator factory for simple retrieval queries"""
    return compose(basic_interaction,
                   map_return(registry(rtype)),
                   map_send(json.loads, attrgetter('content')),
                   oneyield)


@dataclass
class repo(snug.Query[types.Repo]):
    """repository lookup by owner & name"""
    name:  str
    owner: str

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
            params={
                'labels': labels,
                'state':  state,
            })

    @snug.related
    @dataclass
    class issue(snug.Query[types.Issue]):
        """get a specific issue in the repo"""
        repo: 'repo'
        number: int

        @retrieves(types.Issue)
        def __iter__(self):
            return snug.GET(
                f'repos/{self.repo.owner}/'
                f'{self.repo.name}/issues/{self.number}')

        @reusable
        @retrieves(t.List[types.Issue.Comment])
        def comments(issue, since=None):
            """retrieve comments for this issue"""
            return snug.GET(
                f'repos/{issue.repo.owner}/{issue.repo.name}/'
                f'issues/{issue.number}/comments',
                params={'since': since})


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
    return snug.GET('issues', params={
        'filter': filter,
        'state':  state,
        'labels': labels,
        'sort':   sort,
        'since':  since,
    })


@dataclass
class current_user(snug.Query[types.User]):
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


@dataclass
class user(snug.Query[types.User]):
    """retrieve a user by username"""
    username: str

    @retrieves(types.User)
    def __iter__(self):
        return snug.GET(f'users/{self.username}')

    @reusable
    @basic_interaction
    def follow(self):
        """follow this user"""
        response = yield snug.PUT(f'user/following/{self.username}',
                                  headers={'Content-Length': '0'})
        return response.status_code == 204

    @reusable
    @basic_interaction
    def following(self):
        """check if following this user"""
        response = yield snug.GET(f'user/following/{self.username}')
        return response.status_code == 204

    @reusable
    @basic_interaction
    def unfollow(self):
        """unfollow this user"""
        response = yield snug.DELETE(f'user/following/{self.username}')
        return response.status_code == 204
