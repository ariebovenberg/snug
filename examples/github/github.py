from datetime import datetime
import urllib
from typing import Tuple

import snug

partial = snug.utils.ppartial
get_full_url = partial(urllib.parse.urljoin, 'https://api.github.com/')
parse_datetime = partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%SZ')


class Session(snug.Session):
    """github session with simple credentials"""

    def __init__(self, auth: Tuple[str, str]=None):
        super().__init__()
        if auth:
            self.requests.auth = auth
        self.requests.headers.update({
            # explicit API header recommended by docs
            'Accept': 'application/vnd.github.v3+json'
        })


class Organization(snug.json.Resource, session_cls=Session):
    name = snug.Field()
    created_at = snug.Field(load=parse_datetime)
    description = snug.Field()
    email = snug.Field()
    followers = snug.Field()
    following = snug.Field()
    has_organization_projects = snug.Field()
    has_repository_projects = snug.Field()
    id = snug.Field()
    location = snug.Field()
    login = snug.Field()
    public_gists = snug.Field()
    public_repos = snug.Field()
    type = snug.Field()

    @classmethod
    def get(cls, name: str) -> 'Organization':
        return cls.wrap_api_obj(
            cls.session.get(get_full_url('orgs/' + name)).json())
