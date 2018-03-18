import sys

import pytest
from gentools import py2_compatible, return_

import snug


@py2_compatible
def mylist(max_items=5, cursor=0):
    response = yield ('max: {}'.format(max_items), 'cursor: {}'.format(cursor))
    objs = response['objects']
    next_cursor = response['next_cursor']
    if next_cursor is None:
        next_query = None
    else:
        next_query = mylist(max_items=max_items,
                            cursor=next_cursor)
    return_(snug.Page(objs, next=next_query))


py35 = pytest.mark.skipif(sys.version_info < (3, 5, 2),
                          reason='python 3.5.2+ only')
paginated = snug.paginated(mylist(max_items=10))


class MockClient(object):

    def __init__(self, responses):
        self.responses = responses

    def send(self, req):
        return self.responses[req]


class MockAsyncClient(object):

    def __init__(self, responses):
        self.responses = responses

    def send(self, req):
        from .py3_only import awaitable
        return awaitable(self.responses[req])


snug.send.register(MockClient, MockClient.send)
snug.send_async.register(MockAsyncClient, MockAsyncClient.send)


class TestPaginate:

    def test_execute(self):
        mock_client = MockClient({
            ('max: 10', 'cursor: 0'): {
                'objects': list(range(3, 13)),
                'next_cursor': 11
            },
            ('max: 10', 'cursor: 11'): {
                'objects': list(range(13, 23)),
                'next_cursor': '22'
            },
            ('max: 10', 'cursor: 22'): {
                'objects': [1, 4],
                'next_cursor': None
            },
        })
        assert isinstance(paginated, snug.Query)
        paginator = snug.execute(paginated, client=mock_client)

        result = list(paginator)
        assert result == [
            list(range(3, 13)),
            list(range(13, 23)),
            [1, 4],
        ]

    @py35
    def test_execute_async(self, loop):
        from .py35_only import consume_aiter

        mock_client = MockAsyncClient({
            ('max: 10', 'cursor: 0'): {
                'objects': list(range(3, 13)),
                'next_cursor': 11
            },
            ('max: 10', 'cursor: 11'): {
                'objects': list(range(13, 23)),
                'next_cursor': '22'
            },
            ('max: 10', 'cursor: 22'): {
                'objects': [1, 4],
                'next_cursor': None
            },
        })
        paginated = snug.paginated(mylist(max_items=10))
        assert isinstance(paginated, snug.Query)
        paginator = snug.execute_async(paginated, client=mock_client)

        result = loop.run_until_complete(consume_aiter(paginator))
        assert result == [
            list(range(3, 13)),
            list(range(13, 23)),
            [1, 4],
        ]
