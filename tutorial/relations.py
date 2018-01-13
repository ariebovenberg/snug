import json
import snug
from collections import namedtuple

add_prefix = snug.http.prefix_adder('https://api.github.com')
add_headers = snug.https.header_adder({
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'my awesome app',
})

Repository = namedtuple(...)
Issue = namedtuple(...)
User = namedtuple(...)

class ApiException(Exception):
    """an error from the github API"""

def handle_errors(resp):
    """raise a descriptive exception on a "bad request" response"""
    if resp.status_code == 400:
        raise ApiException(json.loads(resp.data).get('message'))
    return resp

def load_json_content(resp):
    """get the response body as JSON"""
    return json.loads(resp.data)

def follow_redirects(req):
    response = yield req
    while response.status_code in (301, 302, 307):
        response = yield req.replace(url=response.headers['Location'])
    return response

class repo(snug.Query):
    """a repository lookup by owner and name"""
    def __init__(self, name, owner):
        self.name, self.owner = name, owner

    @snug.sendmapped(load_json_content, handle_errors)
    @snug.yieldmapped(add_headers, add_prefix, snug.http.GET)
    def __iter__(self):
        return Repository(**(yield f'/repos/{self.owner}/{self.name}'))

    @snug.query(related=True)
    @snug.sendmapped(load_json_content, handle_errors)
    @snug.yieldmapped(add_headers, add_prefix)
    def new_issue(self, title: str, body: str=''):
        """create a new issue in this repo"""
        request = snug.http.POST(
            f'/repos/{self.owner}/{self.name}/issues',
            data=json.dumps({'title': title, 'body': body}))
        return Issue(**(yield request))

    @snug.query(related=True)
    @snug.sendmapped(handle_errors)
    @snug.yieldmapped(add_headers, add_prefix, snug.http.PUT)
    def star(self):
        """star this repo"""
        response = yield f'/user/starred/{self.owner}/{self.name}'
        return response.status_code == 204


class user(snug.Query):
    """a user lookup by name"""
    def __init__(self, username):
        self.username = username

    @snug.sendmapped(load_json_content, handle_errors)
    @snug.yieldmapped(add_headers, add_prefix, snug.http.GET)
    def __iter__(self):
        return User(**(yield f'/users/{self.username}'))

    @snug.query(related=True)
    @snug.sendmapped(handle_errors)
    @snug.yieldmapped(add_headers, add_prefix, snug.http.PUT)
    def follow(self):
        """follow this user"""
        return (yield f'/user/following/{self.username}').status_code == 204

authed_exec = snug.http.authed_exec
