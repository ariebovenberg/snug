import snug

from gentools import py2_compatible, return_


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


class MockClient(object):

    def __init__(self, responses):
        self.responses = responses

    def send(self, req):
        return self.responses[req]


snug.send.register(MockClient, MockClient.send)


class TestPaginate:

    def test_ok(self):
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
        paginated = snug.paginate(mylist(max_items=10))
        paginator = snug.execute(paginated, client=mock_client)

        result = list(paginator)
        assert result == [
            list(range(3, 13)),
            list(range(13, 23)),
            [1, 4],
        ]
