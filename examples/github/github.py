import urllib
import requests
import omgorm as orm
from functools import partial

from typing import Tuple, Union, List, Dict


JsonListOrDict = Union[List, Dict[str, object]]

API_URL = 'https://api.github.com/'
get_full_url = partial(urllib.parse.urljoin, API_URL)


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

    def get(self, resource: str) -> JsonListOrDict:
        """perform a GET request on a resource"""
        assert not resource.endswith('/')
        response = self.requests.get(resource)
        response.raise_for_status()
        return response.json()


class Organization(orm.Resource, session_cls=Session):
    name = orm.json.Field()
    description = orm.json.Field()
    email = orm.json.Field()
    followers = orm.json.Field()
    following = orm.json.Field()
    has_organization_projects = orm.json.Field()
    has_repository_projects = orm.json.Field()
    id = orm.json.Field()
    location = orm.json.Field()
    login = orm.json.Field()
    public_gists = orm.json.Field()
    public_repos = orm.json.Field()
    type = orm.json.Field()

    @classmethod
    def get(cls, name: str) -> 'Organization':
        return cls.wrap_api_obj(
            cls.session.get(get_full_url('orgs/' + name)))
