import json
import typing as t
from pathlib import Path
from functools import partial

import pytest

import snug
import github as gh
from snug.utils import replace

CRED_PATH = Path('~/.snug/github.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

resolve = partial(gh.resolve, auth=auth)

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


def test_all_orgs():
    assert isinstance(all_orgs, snug.Query)
    assert all_orgs.__rtype__ == t.List[gh.Organization]
    assert all_orgs.__req__ == snug.Request('organizations')

    if live:
        orgs = resolve(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


def test_one_org():
    assert isinstance(one_org, snug.Query)
    assert one_org.__rtype__ == gh.Organization
    assert one_org.__req__ == snug.Request('orgs/github')

    if live:
        org = resolve(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


def test_all_repos():
    assert isinstance(all_repos, snug.Query)
    assert all_repos.__rtype__ == t.List[gh.RepoSummary]
    assert all_repos.__req__ == snug.Request('repositories')

    if live:
        repos = resolve(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.RepoSummary)


def test_one_repo():
    assert isinstance(one_repo, snug.Query)
    assert one_repo.__rtype__ == gh.Repo
    assert one_repo.__req__ == snug.Request('repos/github/hub')

    if live:
        repo = resolve(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


def test_assigned_issues():
    assert isinstance(assigned_issues, snug.Query)
    assert assigned_issues.__rtype__ == t.List[gh.Issue]
    assert assigned_issues.__req__ == snug.Request('issues')

    if live:
        issues = resolve(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


def test_current_user():
    assert isinstance(current_user, snug.Query)
    assert current_user.__rtype__ == gh.User
    assert current_user.__req__ == snug.Request('user')

    if live:
        me = resolve(current_user)

        assert isinstance(me, gh.User)


def test_current_user_issues():
    assert isinstance(my_issues, snug.Query)
    assert my_issues.__rtype__ == t.List[gh.Issue]
    assert my_issues.__req__ == snug.Request('user/issues')

    if live:
        issues = resolve(my_issues)
        assert isinstance(issues, list)


def test_all_repo_issues():
    assert isinstance(repo_issues, snug.Query)
    assert repo_issues.__rtype__ == t.List[gh.Issue]
    assert repo_issues.__req__ == snug.Request(
        'repos/github/hub/issues')

    if live:
        issues = resolve(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


def test_one_repo_issue():
    assert isinstance(one_repo_issue, snug.Query)
    assert one_repo_issue.__rtype__ == gh.Issue
    assert one_repo_issue.__req__ == snug.Request(
        'repos/github/hub/issues/123')


def test_filtered_repo_issues():
    assert isinstance(one_repos_fixed_bugs, snug.Query)
    assert one_repos_fixed_bugs.__rtype__ == t.List[gh.Issue]
    assert one_repos_fixed_bugs.__req__ == snug.Request(
        'repos/github/hub/issues', params=dict(labels='bug', state='closed'))

    if live:
        issues = resolve(one_repos_fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)
