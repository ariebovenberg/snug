import json
import snug
from collections import namedtuple

Repository = namedtuple(...)

add_prefix = snug.http.prefix_adder('https://api.github.com')
add_headers = snug.https.header_adder({
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'my awesome app',
})

@snug.querytype()
@snug.yieldmapped(add_headers, add_prefix, snug.http.GET)
def repo(name: str, owner: str):
    """a repository lookup by owner and name"""
    return Repository(**json.loads((yield f'/repos/{owner}/{name}').data))

@snug.querytype()
@snug.yieldmapped(add_headers, add_prefix, snug.http.PUT)
def follow(username: str):
    """follow a user"""
    return (yield f'/user/following/{username}').status_code == 204

exec = snug.http.authed_exec
