import github as gh
import snug

my_github = snug.Session(gh.api)

all_orgs = gh.Organization[:]
one_org = gh.Organization['github']
one_repo = gh.Repo['github', 'gitignore']
all_repos = gh.Repo[:]


def test_all_orgs():
    assert isinstance(all_orgs, snug.Set)
    assert all_orgs == snug.Set(gh.Organization)
    assert all_orgs.request() == snug.Request('organizations')

    orgs = my_github.get(all_orgs)

    assert isinstance(orgs, list)
    assert len(orgs) > 1
    print(orgs)


def test_one_org():
    assert isinstance(one_org, snug.Node)
    assert one_org == snug.Node(gh.Organization, key='github')
    assert one_org.request() == snug.Request('orgs/github')

    org = my_github.get(one_org)

    assert isinstance(org, gh.Organization)
    assert org.login == 'github'
    for field in org.FIELDS.values():
        print('org.{.name}={}'.format(field, getattr(org, field.name)))
    print('retrieving organization: {}'.format(org))


def test_one_repo():
    assert isinstance(one_repo, snug.Node)
    assert one_repo == snug.Node(gh.Repo, key=('github', 'gitignore'))
    assert one_repo.request() == snug.Request('repos/github/gitignore')

    repo = my_github.get(one_repo)
    assert repo.name == 'gitignore'


def test_all_repos():
    assert isinstance(all_repos, snug.Set)
    assert all_repos == snug.Set(gh.Repo)
    assert all_repos.request() == snug.Request('repositories')

    repos = my_github.get(all_repos)

    assert isinstance(repos, list)
    assert len(repos) > 1
    print(repos)
