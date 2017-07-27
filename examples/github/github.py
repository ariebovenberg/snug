from datetime import datetime
import urllib

import snug

partial = snug.utils.ppartial
get_full_url = partial(urllib.parse.urljoin, 'https://api.github.com/')
parse_datetime = partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%SZ')


class Repo(snug.Resource):
    name = snug.Field()


class Organization(snug.Resource):
    avatar_url = snug.Field()
    blog = snug.Field()
    company = snug.Field()
    created_at = snug.Field(load_value=parse_datetime)
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
    repos_url = snug.Field()
    type = snug.Field()

    @classmethod
    def get(cls, name: str) -> 'Organization':
        api_obj = cls.session.get(get_full_url('orgs/' + name)).json()
        return snug.wrap_api_obj(cls, api_obj)


api = snug.Api(headers={'Accept': 'application/vnd.github.v3+json'},
               resources={Organization, Repo})
default_session = snug.Session(snug.Context(api=api, auth=None))
