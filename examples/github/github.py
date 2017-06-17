from datetime import datetime
import urllib
from functools import partial

import omgorm as orm
from omgorm.utils import ppartial

from typing import Tuple, Union, List, Dict


JsonListOrDict = Union[List, Dict[str, object]]

API_URL = 'https://api.github.com/'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
get_full_url = partial(urllib.parse.urljoin, API_URL)

parse_datetime = ppartial(datetime.strptime, ..., DATE_FORMAT)


class Session(orm.Session):
    """github session with simple credentials"""

    def __init__(self, auth: Tuple[str, str]=None):
        super().__init__()
        if auth:
            self.requests.auth = auth
        self.requests.headers.update({
            # explicit API header recommended by docs
            'Accept': 'application/vnd.github.v3+json'
        })


class Organization(orm.json.Resource, session_cls=Session):
    name = orm.Field()
    created_at = orm.Field(load=parse_datetime)
    description = orm.Field()
    email = orm.Field()
    followers = orm.Field()
    following = orm.Field()
    has_organization_projects = orm.Field()
    has_repository_projects = orm.Field()
    id = orm.Field()
    location = orm.Field()
    login = orm.Field()
    public_gists = orm.Field()
    public_repos = orm.Field()
    type = orm.Field()

    @classmethod
    def get(cls, name: str) -> 'Organization':
        return cls.wrap_api_obj(
            cls.session.get(get_full_url('orgs/' + name)).json())
