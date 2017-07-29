from datetime import datetime
import urllib

import snug

partial = snug.utils.ppartial
get_full_url = partial(urllib.parse.urljoin, 'https://api.github.com/')
parse_datetime = partial(datetime.strptime, ..., '%Y-%m-%dT%H:%M:%SZ')


class Repo(snug.Resource):
    name = snug.Field()


class Organization(snug.Resource):
    LIST_URI = 'organizations'
    DETAIL_URI = 'orgs/{}'.format

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
    repos_url = snug.Field()
    type = snug.Field()

    def __str__(self):
        return self.login


def create_url(query: snug.Query) -> str:
    return get_full_url(query.resource.LIST_URI
                        if isinstance(query, snug.Set)
                        else query.resource.DETAIL_URI(query.key))


api = snug.Api(resources={Organization, Repo},
               headers={'Accept': 'application/vnd.github.v3+json'},
               create_url=create_url)
