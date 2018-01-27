import json
from pathlib import Path

import aiohttp
import pytest

import github as gh
import snug

live = pytest.config.getoption('--live')

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
one_repo_issue_comments = one_repo_issue.comments


@pytest.fixture(scope='module')
async def exec():
    async with aiohttp.ClientSession() as client:
        yield snug.async_executor(auth=auth, client=client)


@pytest.mark.asyncio
async def test_all_orgs(exec):

    if live:
        orgs = await exec(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


@pytest.mark.asyncio
async def test_one_org(exec):

    if live:
        org = await exec(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


@pytest.mark.asyncio
async def test_all_repos(exec):

    if live:
        repos = await exec(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.RepoSummary)


@pytest.mark.asyncio
async def test_one_repo(exec):

    if live:
        repo = await exec(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


@pytest.mark.asyncio
async def test_assigned_issues(exec):

    if live:
        issues = await exec(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_current_user(exec):

    if live:
        me = await exec(current_user)

        assert isinstance(me, gh.User)


@pytest.mark.asyncio
async def test_current_user_issues(exec):

    if live:
        issues = await exec(my_issues)
        assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_all_repo_issues(exec):

    if live:
        issues = await exec(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_one_repo_issue(exec):
    if live:
        issue = await exec(one_repo_issue)

        assert isinstance(issue, gh.Issue)


@pytest.mark.asyncio
async def test_filtered_repo_issues(exec):

    if live:
        issues = await exec(one_repos_fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)
