import json
import inspect

from pathlib import Path

import aiohttp
import pytest

import github as gh
import snug

CRED_PATH = Path('~/.snug/github.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

all_orgs = gh.orgs()
one_org = gh.org('github')
one_repo = gh.repo(owner='github', name='hub')
all_repos = gh.repos()

assigned_issues = gh.issues()

current_user = gh.current_user()
my_issues = current_user.issues()

repo_issues = one_repo.issues()
one_repo_issue = one_repo.issue(123)
one_repos_fixed_bugs = repo_issues.replace(labels='bug', state='closed')

live = pytest.config.getoption('--live')


@pytest.fixture(scope='module')
async def aexec():
    async with aiohttp.ClientSession() as client:
        yield gh.authed_aexec(
            auth=auth,
            sender=snug.http.aiohttp_sender(client)
        )


@pytest.mark.asyncio
async def test_all_orgs(aexec):
    # assert next(iter(all_orgs)) == snug.http.GET('organizations')

    if live:
        orgs = await aexec(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


@pytest.mark.asyncio
async def test_one_org(aexec):
    # assert next(iter(one_org)) == snug.http.GET('orgs/github')

    if live:
        org = await aexec(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


@pytest.mark.asyncio
async def test_all_repos(aexec):
    # assert next(iter(all_repos)) == snug.http.GET('repositories')

    if live:
        repos = await aexec(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.RepoSummary)


@pytest.mark.asyncio
async def test_one_repo(aexec):
    # assert next(iter(one_repo)) == snug.http.GET('repos/github/hub')

    if live:
        repo = await aexec(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


@pytest.mark.asyncio
async def test_assigned_issues(aexec):
    # assert next(iter(assigned_issues)) == snug.http.GET('issues')

    if live:
        issues = await aexec(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_current_user(aexec):
    # assert next(iter(current_user)) == snug.http.GET('user')

    if live:
        me = await aexec(current_user)

        assert isinstance(me, gh.User)


@pytest.mark.asyncio
async def test_current_user_issues(aexec):
    # assert next(iter(my_issues)) == snug.http.GET('user/issues')

    if live:
        issues = await aexec(my_issues)
        assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_all_repo_issues(aexec):
    # assert next(iter(repo_issues)) == snug.http.GET(
    #     'repos/github/hub/issues')

    if live:
        issues = await aexec(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_one_repo_issue(aexec):
    # assert next(iter(one_repo_issue)) == snug.http.GET(
    #     'repos/github/hub/issues/123')
    if live:
        issue = await aexec(one_repo_issue)

        assert isinstance(issue, gh.Issue)


@pytest.mark.asyncio
async def test_filtered_repo_issues(aexec):
    # assert next(iter(one_repos_fixed_bugs)) == snug.http.GET(
    #     'repos/github/hub/issues', params=dict(labels='bug', state='closed'))

    if live:
        issues = await aexec(one_repos_fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)
