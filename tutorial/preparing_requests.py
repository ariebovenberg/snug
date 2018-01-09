import json
import snug

API_URL = 'https://api.github.com'

def add_prefix(req):
    return req.replace(url=API_URL+req.url)


@snug.yiedmapped(add_prefix)
@snug.yiedmapped(snug.http.GET)
def repo(name: str, owner: str):
    """a repo lookup by owner and name"""
    response = yield f'/repos/{owner}/{name}'
    return json.loads(response.data)

@snug.yiedmapped(add_prefix)
@snug.yieldmapped(snug.http.GET)
def post_issue(user: str):
    """post an issue"""

@snug.yieldmapped(lambda u: )

exec = snug.lib.basic_exec
