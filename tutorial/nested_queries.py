from datetime import datetime
from dataclasses import dataclass
import snug

@dataclass
class Issue:
    """an issue in a github repo"""
    number:   int
    title:    str

@dataclass
class Repository:
    """a github repository"""
    description: str
    created_at:  datetime

@dataclass
class repo(snug.Query, rtype=Repository):
    """a repository lookup by owner and name"""
    name: str
    owner: str

    def __req__(self):
        return snug.Request(f'api.github.com/repos/{self.owner}/{self.name}')

    @snug.Query(Issue)
    def issue(repo: 'repo', number: int):
        """get an issue in this repository by its number"""
        return snug.Request(
            f'api.github.com/repos/{repo.owner}/{repo.name}/issues/{number}')

resolve = snug.simple_resolve
