import github


session = github.Session()

org = session.Organization.get('github')
print(f'retrieving organization: {org}')

for field in org.fields.values():
    print(f'org.{field.name}={getattr(org, field.name)}')

import pdb; pdb.set_trace()
