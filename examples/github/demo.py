import github
import snug

my_github = snug.Session(github.api)


all_orgs = github.Organization[:]
octocat = github.Organization['octocat']

# orgs = my_github.list(all_orgs)
# print(orgs)


# magic approach
# org = my_github.Organization['github'].get()
# print('retrieving organization: {}'.format(org))

# normal approach
org = my_github.get(octocat)
import pdb; pdb.set_trace()
print('retrieving organization: {}'.format(org))

for field in org.fields.values():
    print('org.{.name}={}'.format(field, getattr(org, field.name)))

import pdb; pdb.set_trace()
