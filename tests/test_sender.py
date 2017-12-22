import snug


def test_piped():

    def ascii_encode(req):
        return (yield req.encode('ascii')).decode('ascii')

    def send(req):
        return {b'/posts/latest/': b'hello'}[req]

    sender = snug.sender.Piped(ascii_encode, send)
    assert sender('/posts/latest/') == 'hello'
