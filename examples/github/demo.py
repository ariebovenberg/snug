import github
import snug

my_github = snug.Session(github.api)


all_orgs = github.Organization[:]
gh_org = github.Organization['github']

orgs = my_github.get(all_orgs)
print(orgs)

org = my_github.get(gh_org)
print('retrieving organization: {}'.format(org))

for field in org.FIELDS.values():
    print('org.{.name}={}'.format(field, getattr(org, field.name)))
