import json
from pathlib import Path
from datetime import datetime

import aiohttp
import pytest

import github as gh

live = pytest.config.getoption('--live')

CRED_PATH = Path('~/.snug/github.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))


@pytest.fixture(scope='module')
async def exec():
    async with aiohttp.ClientSession() as client:
        yield gh.async_executor(auth=auth, client=client)


@pytest.mark.asyncio
async def test_all_orgs(exec):
    all_orgs = gh.orgs()

    if live:
        orgs = await exec(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


@pytest.mark.asyncio
async def test_one_org(exec):
    one_org = gh.org('github')

    if live:
        org = await exec(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


@pytest.mark.asyncio
async def test_all_repos(exec):
    all_repos = gh.repos()

    if live:
        repos = await exec(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.RepoSummary)


@pytest.mark.asyncio
async def test_one_repo(exec):
    one_repo = gh.repo(owner='github', name='hub')

    if live:
        repo = await exec(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


@pytest.mark.asyncio
async def test_assigned_issues(exec):
    assigned_issues = gh.issues()

    if live:
        issues = await exec(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_current_user(exec):
    if live:
        me = await exec(gh.CURRENT_USER)

        assert isinstance(me, gh.User)


@pytest.mark.asyncio
async def test_current_user_issues(exec):
    my_issues = gh.CURRENT_USER.issues()

    if live:
        issues = await exec(my_issues)
        assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_all_repo_issues(exec):
    repo_issues = gh.repo('hub', owner='github').issues()

    if live:
        issues = await exec(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_one_repo_issue(exec):
    one_repo_issue = gh.repo('hub', owner='github').issue(123)
    if live:
        issue = await exec(one_repo_issue)

        assert isinstance(issue, gh.Issue)


@pytest.mark.asyncio
async def test_filtered_repo_issues(exec):
    fixed_bugs = (gh.repo('hub', owner='github')
                  .issues(labels='bug', state='closed'))

    if live:
        issues = await exec(fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


@pytest.mark.asyncio
async def test_issue_comments(exec):
    query = (gh.repo('Hello-World', owner='octocat')
             .issue(348)
             .comments(since=datetime(2018, 1, 1)))

    if live:
        comments = await exec(query)

        assert isinstance(comments, list)
        assert isinstance(comments[0], gh.Issue.Comment)


@pytest.mark.asyncio
async def test_follow_user(exec):
    user = gh.user('octocat')

    if live:
        assert await exec(user.follow())
        assert await exec(user.unfollow())
        assert not await exec(user.following())
