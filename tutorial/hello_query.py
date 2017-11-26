import snug

@snug.Query
def repo(name: str, owner: str):
    """a repository lookup by owner and name"""
    return snug.Request(f'api.github.com/repos/{owner}/{name}')

resolve = snug.simple_resolve
