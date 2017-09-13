import json
from pathlib import Path

import github as gh
import snug

CRED_PATH = Path('~/.snug/github.json').expanduser()
auth = tuple(json.loads(CRED_PATH.read_bytes()))

my_github = snug.Session(gh.api, auth=auth)

all_orgs = gh.Organization[:]
one_org = gh.Organization['github']
one_repo = gh.Repo['github', 'gitignore']
all_repos = gh.Repo[:]

assigned_issues = gh.Issue.ASSIGNED
one_issue = gh.Issue['github', 'gitignore', 123]

current_user = gh.User.CURRENT
my_issues = current_user.issues

repo_issues = one_repo.issues
one_repo_issue = one_repo.issues[123]


def test_all_orgs():
    assert isinstance(all_orgs, snug.FilteredSet)
    assert snug.req(all_orgs) == snug.Request('organizations')

    orgs = my_github.get(all_orgs)

    assert isinstance(orgs, list)
    assert len(orgs) > 1
    print(orgs)


def test_one_org():
    assert isinstance(one_org, snug.Lookup)
    assert snug.req(one_org) == snug.Request('orgs/github')

    org = my_github.get(one_org)

    assert isinstance(org, gh.Organization)
    assert org.login == 'github'
    for field in org.FIELDS.values():
        print('org.{.name}={}'.format(field, getattr(org, field.name)))
    print('retrieving organization: {}'.format(org))


def test_all_repos():
    assert isinstance(all_repos, snug.FilteredSet)
    assert snug.req(all_repos) == snug.Request('repositories')

    repos = my_github.get(all_repos)

    assert isinstance(repos, list)
    assert len(repos) > 1
    assert isinstance(repos[0], gh.Repo)
    print(repos)


def test_one_repo():
    assert isinstance(one_repo, snug.Lookup)
    assert snug.req(one_repo) == snug.Request('repos/github/gitignore')

    repo = my_github.get(one_repo)

    assert isinstance(repo, gh.Repo)
    assert repo.name == 'gitignore'
    print(repo)


def test_assigned_issues():
    assert isinstance(assigned_issues, snug.Set)
    assert snug.req(assigned_issues) == snug.Request('issues')

    issues = my_github.get(assigned_issues)

    assert isinstance(issues, list)
    assert len(issues) > 1
    assert isinstance(issues[0], gh.Issue)


def test_one_issue():
    assert isinstance(one_issue, snug.Lookup)
    assert snug.req(one_issue) == snug.Request(
        'repos/github/gitignore/issues/123')

    issue = my_github.get(one_issue)

    assert isinstance(issue, gh.Issue)


def test_current_user():
    assert isinstance(current_user, snug.Node)
    assert snug.req(current_user) == snug.Request('user')

    me = my_github.get(current_user)

    assert isinstance(me, gh.User)


def test_current_user_issues():
    assert isinstance(my_issues, snug.Set)
    assert snug.req(my_issues) == snug.Request('user/issues')

    issues = my_github.get(my_issues)

    assert isinstance(issues, list)


def test_all_repo_issues():
    assert isinstance(repo_issues, snug.IndexableSet)
    assert snug.req(repo_issues) == snug.Request(
        'repos/github/gitignore/issues')

    issues = my_github.get(repo_issues)

    assert isinstance(issues, list)
    assert len(issues) > 1
    assert isinstance(issues[0], gh.Issue)


def test_one_repo_issue():
    assert isinstance(one_repo_issue, snug.Lookup)
    assert snug.req(one_repo_issue) == snug.Request(
        'repos/github/gitignore/issues/123'
    )
