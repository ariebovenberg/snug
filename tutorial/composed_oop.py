import json
import snug
import typing as t
from collections import namedtuple

Repository = namedtuple(...)

class ApiException(Exception):
    """an error from the github API"""

def load_repo(jsondata: dict) -> Repository:
    ...  # deserialization logic

T = t.TypeVar('T')

# typevar allows us to subclass `BaseQuery` as a generic, not required
class BaseQuery(snug.Query[T]):
    """base class for github queries"""

    def prepare(self, request):
        """add headers and stuff"""
        return (request.with_prefix('https://api.github.com')
                .with_headers({
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'my awesome app',
                }))

    def __iter__(self):
        """perform the query, while handling redirects"""
        req = self.prepare(self.request)
        resp = yield req
        while resp.status_code in (301, 302, 307):
            resp = yield req.replace(url=resp.headers['Location'])
        return self.load(self.check_response(resp))

    def check_response(self, resp):
        """raise a descriptive exception on a "bad request" response"""
        if resp.status_code == 400:
            raise ApiException(json.loads(resp.content).get('message'))
        return resp

class repo(BaseQuery[Repository]):
    """a repository lookup by owner and name"""
    def __init__(self, name: str, owner: str):
        self.request = snug.GET(f'/repos/{owner}/{name}')

    def load(self, response):
        return load_repo(json.loads(response.content))


class follow(BaseQuery[bool]):
    """follow another user"""
    def __init__(self, name: str):
        self.request == snug.PUT(f'/user/following/{name}')

    def load(self, response):
        return response.status_code == 204
