import json
import snug
from gentools import reusable, map_yield, map_send

add_prefix = snug.prefix_adder('https://api.github.com')
add_headers = snug.header_adder({
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'my awesome app',
})

class ApiException(Exception):
    """an error from the github API"""

def handle_errors(resp):
    """raise a descriptive exception on a "bad request" response"""
    if resp.status_code == 400:
        raise ApiException(json.loads(resp.content).get('message'))
    return resp

def load_json_content(resp):
    """get the response body as JSON"""
    return json.loads(resp.content)

@reusable
@map_send(load_json_content, handle_errors)
@map_yield(add_headers, add_prefix, snug.GET)
def repo(name: str, owner: str) -> snug.Query[dict]:
    """a repository lookup by owner and name"""
    return (yield f'/repos/{owner}/{name}')

@reusable
@map_send(handle_errors)
@map_yield(add_headers, add_prefix, snug.PUT)
def follow(username: str) -> snug.Query[bool]:
    """follow a user"""
    return (yield f'/user/following/{username}').status_code == 204
