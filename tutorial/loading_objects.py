from datetime import datetime
from dataclasses import dataclass  # PEP 557
import snug

@dataclass
class Repository:
    """a github repository"""
    description: str
    created_at:  datetime

@snug.Query(Repository)
def repo(name: str, owner: str):
    """a repository lookup by owner and name"""
    return snug.Request(f'api.github.com/repos/{owner}/{name}')

resolve = snug.simple_resolve
