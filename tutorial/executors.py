import json
import snug

@snug.querytype()
def repo(name: str, owner: str):
    """a repo lookup by owner and name"""
    request = snug.http.GET(f'https://api.github.com/repos/{owner}/{name}')
    response = yield request
    return json.loads(response.data)

@snug.querytype()
def follow(username: str):
    """follow a user"""
    request = snug.http.PUT(f'https://api.github.com/user/following/{username}')
    response = yield request
    return response.status_code == 204

exec = snug.http.simple_exec()
"""executor (without authentication)"""
authed_exec = snug.http.authed_exec
"""factory for authenticated executors"""
authed_aexec = snug.http.authed_aexec
"""factory for asynchronous, authenticated executors"""
