import json
import snug
from gentools import map_yield, reusable

add_prefix = snug.prefix_adder('https://api.github.com')
add_headers = snug.header_adder({
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'my awesome app',
})

@reusable
@map_yield(add_headers, add_prefix, snug.GET)
def repo(name: str, owner: str) -> snug.Query[dict]:
    """a repository lookup by owner and name"""
    return json.loads((yield f'/repos/{owner}/{name}').content)

@reusable
@map_yield(add_headers, add_prefix, snug.PUT)
def follow(username: str) -> snug.Query[bool]:
    """follow a user"""
    return (yield f'/user/following/{username}').status_code == 204
