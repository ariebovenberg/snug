import github
import snug

my_github = snug.Session(github.api)


all_orgs = github.Organization[:]
some_org = github.Organization['github']


def test_get_all_orgs():
    orgs = my_github.get(all_orgs)
    print(orgs)
    assert len(orgs) > 1


def test_get_one_org():
    org = my_github.get(some_org)
    assert isinstance(org, github.Organization)
    print('retrieving organization: {}'.format(org))
    for field in org.FIELDS.values():
        print('org.{.name}={}'.format(field, getattr(org, field.name)))

