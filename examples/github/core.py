import enum
import operator
import reprlib
import typing as t
from datetime import datetime
from operator import truth

import snug
from toolz import flip, partial, valfilter
from dataclasses import dataclass, asdict

parse_datetime = partial(flip(datetime.strptime), '%Y-%m-%dT%H:%M:%SZ')

_repr = reprlib.Repr()
_repr.maxstring = 45


api = snug.Api('https://api.github.com/',
               headers={'Accept': 'application/vnd.github.v3+json'},
               parse_response=operator.methodcaller('json'))


class Repo(snug.Resource):
    """a github repository"""
    name = snug.Field()
    archive_url = snug.Field()
    assignees_url = snug.Field()
    blobs_url = snug.Field()
    branches_url = snug.Field()
    clone_url = snug.Field()
    collaborators_url = snug.Field()
    comments_url = snug.Field()
    commits_url = snug.Field()
    compare_url = snug.Field()
    contents_url = snug.Field()
    contributors_url = snug.Field()
    created_at = snug.Field(load=parse_datetime)
    default_branch = snug.Field()
    deployments_url = snug.Field()
    description = snug.Field()
    downloads_url = snug.Field()
    events_url = snug.Field()
    fork = snug.Field()
    forks = snug.Field()
    forks_count = snug.Field()
    forks_url = snug.Field()
    full_name = snug.Field()
    git_commits_url = snug.Field()
    git_refs_url = snug.Field()
    git_tags_url = snug.Field()
    git_url = snug.Field()
    has_downloads = snug.Field()
    has_issues = snug.Field()
    has_pages = snug.Field()
    has_projects = snug.Field()
    has_wiki = snug.Field()
    homepage = snug.Field()
    hooks_url = snug.Field()
    html_url = snug.Field()
    id = snug.Field()
    issue_comment_url = snug.Field()
    issue_events_url = snug.Field()
    issues_url = snug.Field()
    keys_url = snug.Field()
    labels_url = snug.Field()
    language = snug.Field()
    languages_url = snug.Field()
    merges_url = snug.Field()
    milestones_url = snug.Field()
    mirror_url = snug.Field()
    name = snug.Field()
    notifications_url = snug.Field()
    open_issues = snug.Field()
    open_issues_count = snug.Field()
    owner = snug.Field()
    permissions = snug.Field()
    private = snug.Field()
    pulls_url = snug.Field()
    pushed_at = snug.Field()
    releases_url = snug.Field()
    size = snug.Field()
    ssh_url = snug.Field()
    stargazers_count = snug.Field()
    stargazers_url = snug.Field()
    statuses_url = snug.Field()
    subscribers_url = snug.Field()
    subscription_url = snug.Field()
    svn_url = snug.Field()
    tags_url = snug.Field()
    teams_url = snug.Field()
    trees_url = snug.Field()
    updated_at = snug.Field()
    url = snug.Field()
    watchers = snug.Field()
    watchers_count = snug.Field()

    def __str__(self):
        return '{} - {}'.format(
            self.name, _repr.repr(self.description))

    @dataclass(frozen=True)
    class lookup(snug.Item):
        """repository lookup by owner & name"""
        owner: str
        name:  str

        def __request__(self):
            return snug.Request(f'repos/{self.owner}/{self.name}')

        @dataclass
        class issues(snug.Indexable, snug.Set):
            """a set of issues for a repository"""
            repo: 'Repo.lookup'
            labels: str = None
            state: str = None

            def __request__(self):
                params = asdict(self)
                params.pop('repo')
                return snug.Request(
                    f'repos/{self.repo.owner}/{self.repo.name}/issues',
                    params=valfilter(truth, params))

        @dataclass(frozen=True)
        class issue(snug.Item):
            repo: 'Repo.lookup'
            number: int

            def __request__(self):
                return snug.Request(
                    f'repos/{self.repo.owner}/'
                    f'{self.repo.name}/issues/{self.number}')

    @dataclass(frozen=True)
    class selection(snug.Set):
        """a selection on repositories"""

        def __request__(self):
            return snug.Request('repositories')


class Organization(snug.Resource):
    """a github organization"""
    avatar_url = snug.Field()
    blog = snug.Field()
    company = snug.Field()
    created_at = snug.Field(load=parse_datetime)
    description = snug.Field()
    email = snug.Field()
    events_url = snug.Field()
    followers = snug.Field()
    following = snug.Field()
    has_organization_projects = snug.Field()
    has_repository_projects = snug.Field()
    hooks_url = snug.Field()
    html_url = snug.Field()
    id = snug.Field()
    issues_url = snug.Field()
    location = snug.Field()
    login = snug.Field()
    members_url = snug.Field()
    name = snug.Field()
    public_gists = snug.Field()
    public_members_url = snug.Field()
    public_repos = snug.Field()
    repos_url = snug.Field()
    type = snug.Field()

    @dataclass(frozen=True)
    class lookup(snug.Item):
        """Organization lookup by login"""
        login: str

        def __request__(self):
            return snug.Request(f'orgs/{self.login}')

    @dataclass(frozen=True)
    class selection(snug.Set):

        def __request__(self):
            return snug.Request('organizations')

    def __str__(self):
        try:
            return self.name
        except KeyError:
            return self.login


class Issue(snug.Resource):
    """a github issue or pull-request"""
    number = snug.Field()
    title = snug.Field()
    body = snug.Field()
    state = snug.Field()

    def __str__(self):
        return f'#{self.number} {self.title}'

    class State(enum.Enum):
        OPEN = 'open'
        CLOSED = 'closed'
        ALL = 'all'

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

    @dataclass
    class lookup(snug.Item):
        """an issue referenced by repo & number"""
        repo: t.Union['Repo', 'Repo.lookup']
        number: int

        def __request__(self):
            return snug.Request(f'repos/{self.repo.owner}/{self.repo.name}/'
                                f'issues/{self.number}')

    @dataclass
    class selection(snug.Set):
        """a selection of assigned issues"""
        filter: t.Optional[str] = None
        state:  t.Optional['Issue.State'] = None
        labels: t.Optional[str] = None
        sort:   t.Optional['Issue.Sort'] = None
        since:  t.Optional[datetime] = None

        def __request__(self):
            params = valfilter(truth, asdict(self))
            return snug.Request('issues', params=params)


class User(snug.Resource):
    """a github user"""
    avatar_url = snug.Field()
    bio = snug.Field()
    blog = snug.Field()
    company = snug.Field()
    created_at = snug.Field()
    email = snug.Field()
    events_url = snug.Field()
    followers = snug.Field()
    followers_url = snug.Field()
    following = snug.Field()
    following_url = snug.Field()
    gists_url = snug.Field()
    gravatar_id = snug.Field()
    hireable = snug.Field()
    html_url = snug.Field()
    id = snug.Field()
    location = snug.Field()
    login = snug.Field()
    name = snug.Field()
    organizations_url = snug.Field()
    public_gists = snug.Field()
    public_repos = snug.Field()
    received_events_url = snug.Field()
    repos_url = snug.Field()
    site_admin = snug.Field()
    starred_url = snug.Field()
    subscriptions_url = snug.Field()
    updated_at = snug.Field()
    url = snug.Field()

    class _Current(snug.Item):

        def __request__(self):
            return snug.Request('user')

        @dataclass(frozen=True)
        class issues(snug.Set):
            user: 'User'

            def __request__(self):
                return snug.Request('user/issues')

    CURRENT = _Current()
    """a reference to the current user"""


# TODO: set this more nicely
Repo.lookup.issues.TYPE = Issue
Repo.lookup.issue.TYPE = Issue
User._Current.issues.TYPE = Issue
