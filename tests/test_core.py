import snug


def test_resolve():
    sender = {'/posts/latest/': b'hello world'}.__getitem__

    class MyQuery:
        def __resolve__(self):
            return (yield '/posts/latest/').decode('ascii')

    assert snug.resolve(sender, MyQuery()) == 'hello world'
