import json
from pathlib import Path

import pytest

import snug
import github as gh

CRED_PATH = Path('~/.snug/github.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

my_github = snug.Session(gh.api, auth=auth)

all_orgs = gh.orgs()
one_org = gh.org('github')
one_repo = gh.repo('github', 'hub')
all_repos = gh.repos()

assigned_issues = gh.issues()
one_issue = gh.issue(one_repo, number=123)

current_user = gh.current_user()
my_issues = current_user.issues()

repo_issues = one_repo.issues()
one_repo_issue = one_repo.issue(123)
one_repos_fixed_bugs = repo_issues.select(labels='bug', state='closed')

live = pytest.config.getoption('--live')


def test_all_orgs():
    assert isinstance(all_orgs, snug.Set)
    assert snug.req(all_orgs) == snug.Request('organizations')

    if live:
        orgs = my_github.get(all_orgs)

        assert isinstance(orgs, list)
        assert len(orgs) > 1


def test_one_org():
    assert isinstance(one_org, snug.Item)
    assert snug.req(one_org) == snug.Request('orgs/github')

    if live:
        org = my_github.get(one_org)

        assert isinstance(org, gh.Organization)
        assert org.login == 'github'


def test_all_repos():
    assert isinstance(all_repos, snug.Set)
    assert snug.req(all_repos) == snug.Request('repositories')

    if live:
        repos = my_github.get(all_repos)

        assert isinstance(repos, list)
        assert len(repos) > 1
        assert isinstance(repos[0], gh.Repo)


def test_one_repo():
    assert isinstance(one_repo, snug.Item)
    assert snug.req(one_repo) == snug.Request('repos/github/hub')

    if live:
        repo = my_github.get(one_repo)

        assert isinstance(repo, gh.Repo)
        assert repo.name == 'hub'


def test_assigned_issues():
    assert isinstance(assigned_issues, snug.Set)
    assert snug.req(assigned_issues) == snug.Request('issues')

    if live:
        issues = my_github.get(assigned_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


def test_one_issue():
    assert isinstance(one_issue, snug.Item)
    assert snug.req(one_issue) == snug.Request(
        'repos/github/hub/issues/123')

    if live:
        issue = my_github.get(one_issue)

        assert isinstance(issue, gh.Issue)


def test_current_user():
    assert isinstance(current_user, snug.Item)
    assert snug.req(current_user) == snug.Request('user')

    if live:
        me = my_github.get(current_user)

        assert isinstance(me, gh.User)


def test_current_user_issues():
    assert isinstance(my_issues, snug.Set)
    assert snug.req(my_issues) == snug.Request('user/issues')
    assert repo_issues.type is gh.Issue

    if live:
        issues = my_github.get(my_issues)
        assert isinstance(issues, list)


def test_all_repo_issues():
    assert isinstance(repo_issues, snug.Set)
    assert snug.req(repo_issues) == snug.Request(
        'repos/github/hub/issues')
    assert repo_issues.type is gh.Issue

    if live:
        issues = my_github.get(repo_issues)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)


def test_one_repo_issue():
    assert isinstance(one_repo_issue, snug.Item)
    assert snug.req(one_repo_issue) == snug.Request(
        'repos/github/hub/issues/123')
    assert one_repo_issue.type is gh.Issue


def test_filtered_repo_issues():
    assert isinstance(one_repos_fixed_bugs, snug.Set)
    assert snug.req(one_repos_fixed_bugs) == snug.Request(
        'repos/github/hub/issues', params=dict(labels='bug', state='closed'))
    assert one_repos_fixed_bugs.type is gh.Issue

    if live:
        issues = my_github.get(one_repos_fixed_bugs)

        assert isinstance(issues, list)
        assert len(issues) > 1
        assert isinstance(issues[0], gh.Issue)
