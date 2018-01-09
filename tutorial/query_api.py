import json
import snug

class repo(snug.Query):
    """a repository lookup by owner and name"""
    def __init__(self, name: str, owner: str):
        self.name, self.owner = name, owner

    def __iter__(self):
        request = snug.http.GET(
            f'https://api.github.com/repos/{self.owner}/{self.name}')
        response = yield request
        return json.loads(response.data)

exec = snug.http.simple_exec()
