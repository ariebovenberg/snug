from datetime import datetime
import urllib

import snug

partial = snug.utils.ppartial
get_full_url = partial(urllib.parse.urljoin, 'https://api.github.com/')
parse_datetime = partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%SZ')

HEADERS = {'Accept': 'application/vnd.github.v3+json'}


class Session(snug.Session):
    pass


class Repo(snug.json.Resource, session_cls=Session):
    name = snug.Field()


def load_repos(url):
    import pdb; pdb.set_trace()


class Organization(snug.json.Resource, session_cls=Session):
    avatar_url = snug.Field()
    blog = snug.Field()
    company = snug.Field()
    created_at = snug.Field(load=parse_datetime)
    description = snug.Field()
    email = snug.Field()
    events_url = snug.Field()
    followers = snug.Field()
    following = snug.Field()
    has_organization_projects = snug.Field()
    has_repository_projects = snug.Field()
    hooks_url = snug.Field()
    html_url = snug.Field()
    id = snug.Field()
    issues_url = snug.Field()
    location = snug.Field()
    login = snug.Field()
    members_url = snug.Field()
    name = snug.Field()
    public_gists = snug.Field()
    public_members_url = snug.Field()
    public_repos = snug.Field()
    repos_url = snug.Field(load=load_repos)
    type = snug.Field()

    @classmethod
    def get(cls, name: str) -> 'Organization':
        return cls.wrap_api_obj(
            cls.session.get(get_full_url('orgs/' + name)).json())
