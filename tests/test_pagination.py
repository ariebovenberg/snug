import snug

from gentools import py2_compatible, return_


@py2_compatible
def mylist(max_items=5, cursor=0):
    response = yield ('max {}'.format(max_items), 'cursor: {}'.format(cursor))
    objs = response['objects']
    next_cursor = response['next_cursor']
    return_(snug.Page(objs, next=mylist(max_items=max_items,
                                        cursor=next_cursor)))


class MockClient(object):

    def __init__(self, responses):
        self.response = responses

    def send(self, req):
        return self.responses[req]


snug.send.register(MockClient, MockClient.send)


class TestPaginate:

    def test_ok(self):
        mock_client = MockClient({
            ('max: 10', 'cursor: 0'): {'objects': list(range(3, 13))},
            ('max: 10', 'cursor: 11'): {'objects': list(range(13, 23))},
        })

        paginated = snug.paginate(mylist(max_items=10))
        paginator = snug.execute(paginated, client=mock_client)

        assert list(paginated(mylist()))
