"""the main API"""
import abc
import json
import reprlib
import typing as t
from datetime import datetime
from functools import singledispatch
from operator import methodcaller

from dataclasses import dataclass

import snug

from .types import (Repo, Issue, RepoSummary, Organization,
                    OrganizationSummary, User)
from .load import registry

API_PREFIX = 'https://api.github.com/'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}

_repr = reprlib.Repr()
_repr.maxstring = 45

execute = snug.execute
execute_async = snug.execute_async
executor = snug.executor
async_executor = snug.async_executor


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


T = t.TypeVar('T')


class BaseQuery(snug.Query[T]):
    """Base query functionality"""

    @staticmethod
    def prepare(request):
        return prepare_params(
            request
            .with_prefix(API_PREFIX)
            .with_headers(HEADERS))

    def __iter__(self):
        response = yield self.prepare(self.request)
        return self.parse(response)

    @staticmethod
    def parse(response):
        """check for errors"""
        if response.status_code == 400:
            try:
                msg = json.loads(response.content)['message']
            except (KeyError, ValueError):
                msg = ''
            raise ApiError(msg)
        return response


class Retrieval(BaseQuery[T]):
    """base for retrieval queries"""
    @abc.abstractproperty
    def type(self): pass

    def parse(self, response):
        parsed = super().parse(response)
        loader = registry(self.type)
        return loader(json.loads(parsed.content))


@dataclass
class repo(Retrieval):
    """repository lookup by owner & name"""
    type = Repo
    name:  str
    owner: str

    @property
    def request(self):
        return snug.GET(f'repos/{self.owner}/{self.name}')

    @snug.related
    @dataclass
    class issues(Retrieval):
        """get the issues for this repo"""
        type = t.List[Issue]
        repo:   'repo'
        labels: t.Optional[str] = None
        state:  t.Optional[str] = None

        @property
        def request(self):
            return snug.GET(
                f'repos/{self.repo.owner}/{self.repo.name}/issues',
                params={'labels': self.labels, 'state':  self.state})

    @snug.related
    @dataclass
    class issue(Retrieval):
        """get a specific issue in the repo"""
        type = Issue
        repo: 'repo'
        number: int

        @property
        def request(self):
            return snug.GET(
                f'repos/{self.repo.owner}/'
                f'{self.repo.name}/issues/{self.number}')

        @snug.related
        @dataclass
        class comments(Retrieval):
            """retrieve comments for this issue"""
            type = t.List[Issue.Comment]
            issue: 'issue'
            since: t.Optional[datetime] = None

            @property
            def request(self):
                return snug.GET(
                    f'repos/{self.issue.repo.owner}/{self.issue.repo.name}/'
                    f'issues/{self.issue.number}/comments',
                    params={'since': self.since})


@dataclass
class repos(Retrieval):
    """list of repositories"""
    type = t.List[RepoSummary]
    request = snug.GET('repositories')


@dataclass
class org(Retrieval):
    """Organization lookup by login"""
    type = Organization
    login: str

    @property
    def request(self):
        return snug.GET(f'orgs/{self.login}')


@dataclass
class orgs(Retrieval):
    """a selection of organizations"""
    type = t.List[OrganizationSummary]
    request = snug.GET('organizations')


@dataclass
class issues(Retrieval):
    """a selection of assigned issues"""
    type = t.List[Issue]
    filter: t.Optional[str] = None
    state:  t.Optional[Issue.State] = None
    labels: t.Optional[str] = None
    sort:   t.Optional[Issue.Sort] = None
    since:  t.Optional[datetime] = None

    @property
    def request(self):
        return snug.GET('issues', params={
            'filter': self.filter,
            'state':  self.state,
            'labels': self.labels,
            'sort':   self.sort,
            'since':  self.since,
        })


@dataclass
class current_user(Retrieval):
    """a reference to the current user"""
    type = User
    request = snug.GET('user')

    @dataclass
    class issues(Retrieval):
        type = t.List[Issue]
        request = snug.GET('user/issues')


CURRENT_USER = current_user()


@dataclass
class user(Retrieval):
    """retrieve a user by username"""
    type = User
    username: str

    @property
    def request(self):
        return snug.GET(f'users/{self.username}')

    @snug.related
    @dataclass
    class follow(BaseQuery):
        """follow this user"""
        user: 'user'

        @property
        def request(self):
            return snug.PUT(f'user/following/{self.user.username}',
                            headers={'Content-Length': '0'})

        def parse(self, response):
            return response.status_code == 204

    @snug.related
    @dataclass
    class following(BaseQuery):
        """check if following this user"""
        user: 'user'

        @property
        def request(self):
            return snug.GET(f'user/following/{self.user.username}')

        def parse(self, response):
            return response.status_code == 204

    @snug.related
    @dataclass
    class unfollow(BaseQuery):
        """unfollow this user"""
        user: 'user'

        @property
        def request(self):
            return snug.DELETE(f'user/following/{self.user.username}')

        def parse(self, response):
            return response.status_code == 204
