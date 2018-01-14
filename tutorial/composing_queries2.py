import json
import snug
from collections import namedtuple

Repository = namedtuple(...)

add_prefix = snug.http.prefix_adder('https://api.github.com')
add_headers = snug.https.header_adder({
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'my awesome app',
})

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

@snug.querytype()
@snug.sendmapped(load_json_content, handle_errors)
@snug.yieldmapped(add_headers, add_prefix, snug.http.GET)
def repo(name: str, owner: str):
    """a repository lookup by owner and name"""
    return Repository(**(yield f'/repos/{owner}/{name}'))

@snug.querytype()
@snug.sendmapped(handle_errors)
@snug.yieldmapped(add_headers, add_prefix, snug.http.PUT)
def follow(username: str):
    """follow a user"""
    return (yield f'/user/following/{username}').status_code == 204

exec = snug.http.authed_exec
