"""separate objects only importable on python 3.5+"""


async def consume_aiter(iterable):
    """consume an async iterable to a list"""
    result = []
    async for item in iterable:
        result.append(item)
    return result
