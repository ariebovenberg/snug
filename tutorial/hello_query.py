import json
import snug

@snug.querytype()
def repo(name: str, owner: str):
    """a repo lookup by owner and name"""
    request = snug.http.GET(f'https://api.github.com/repos/{owner}/{name}')
    response = yield request
    return json.loads(response.data)

exec = snug.http.simple_exec()
