import snug


def test_resolve(resolver, query, Post):
    response = snug.resolve(resolver, query)
    assert response == [
        Post(5, 'hello world'),
        Post(6, 'goodbye'),
    ]
