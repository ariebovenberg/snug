import json
from dataclasses import replace
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
one_repos_fixed_bugs = replace(repo_issues, labels='bug', state='closed')

live = pytest.config.getoption('--live')


@pytest.fixture(scope='module')
async def resolver():
    async with aiohttp.ClientSession() as client:
        yield gh.async_resolver(
            auth=auth,
            sender=snug.http.aiohttp_sender(client)
        )


@pytest.mark.asyncio
async def test_all_orgs(resolver):
    assert all_orgs._request() == snug.Request('organizations')

    if live:
        orgs = await resolver(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


@pytest.mark.asyncio
async def test_one_org(resolver):
    assert one_org._request() == snug.Request('orgs/github')

    if live:
        org = await resolver(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


@pytest.mark.asyncio
async def test_all_repos(resolver):
    assert all_repos._request() == snug.Request('repositories')

    if live:
        repos = await resolver(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.RepoSummary)


@pytest.mark.asyncio
async def test_one_repo(resolver):
    assert one_repo._request() == snug.Request('repos/github/hub')

    if live:
        repo = await resolver(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


@pytest.mark.asyncio
async def test_assigned_issues(resolver):
    assert assigned_issues._request() == snug.Request('issues')

    if live:
        issues = await resolver(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_current_user(resolver):
    assert current_user._request() == snug.Request('user')

    if live:
        me = await resolver(current_user)

        assert isinstance(me, gh.User)


@pytest.mark.asyncio
async def test_current_user_issues(resolver):
    assert my_issues._request() == snug.Request('user/issues')

    if live:
        issues = await resolver(my_issues)
        assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_all_repo_issues(resolver):
    assert repo_issues._request() == snug.Request('repos/github/hub/issues')

    if live:
        issues = await resolver(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_one_repo_issue(resolver):
    assert one_repo_issue._request() == snug.Request(
        'repos/github/hub/issues/123')


@pytest.mark.asyncio
async def test_filtered_repo_issues(resolver):
    assert one_repos_fixed_bugs._request() == snug.Request(
        'repos/github/hub/issues', params=dict(labels='bug', state='closed'))

    if live:
        issues = await resolver(one_repos_fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)
