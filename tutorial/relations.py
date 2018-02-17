import json
import snug

BASE = 'https://api.github.com'

class repo(snug.Query[dict]):
    """a repository lookup by owner and name"""
    def __init__(self, name, owner):
        self.name, self.owner = name, owner

    def __iter__(self):
        request = snug.GET(BASE + f'/repos/{self.owner}/{self.name}')
        return json.loads((yield request).content)

    def star(self) -> snug.Query[bool]:
        """star this repo"""
        req = snug.PUT(BASE + f'/user/starred/{self.owner}/{self.name}')
        return (yield req).status_code == 204

    @snug.related
    class issue(snug.Query[dict]):
        """get an issue in this repo"""
        def __init__(self, repo, number):
            self.repo, self.number = repo, number

        def __iter__(self):
            request = snug.GET(
                BASE +
                f'repos/{self.repo.owner}/'
                f'{self.repo.name}/issues/{self.number}')
            return json.loads((yield request).content)

        def comments(self, since: datetime) -> snug.Query[list]:
            """retrieve comments for this issue"""
            request = snug.GET(
                BASE +
                f'repos/{self.issue.repo.owner}/{self.issue.repo.name}/'
                f'issues/{self.issue.number}/comments',
                params={'since': since.strftime('%Y-%m-%dT%H:%M:%SZ')})
            return json.loads((yield request).content)
