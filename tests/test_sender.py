import snug


def test_piped(jsonwrapper):

    def _sender(request):
        return snug.Response(
            404,
            data='{{"error": "{} not found"}}'.format(request.url)
            .encode('ascii'))

    sender = snug.sender.Piped(_sender, pipe=jsonwrapper)
    response = sender(snug.Request('my/url', {'foo': 4}))
    assert response == {'error': 'my/url not found'}
