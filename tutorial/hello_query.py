import json
import snug

def repo(name: str, owner: str):
    """a repo lookup by owner and name"""
    request = snug.GET(
        f'https://api.github.com/repos/{owner}/{name}')
    response = yield request
    return json.loads(response.data)
