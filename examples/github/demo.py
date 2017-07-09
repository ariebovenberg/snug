import requests
import github


req_session = requests.Session()
req_session.headers.update(github.HEADERS)


session = github.Session(req_session)

org = session.Organization.get('github')
print('retrieving organization: {}'.format(org))

for field in org.fields.values():
    print('org.{.name}={}'.format(field, getattr(org, field.name)))

import pdb; pdb.set_trace()
